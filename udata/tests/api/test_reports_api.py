from datetime import datetime

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.reports.constants import (
    REASON_ILLEGAL_CONTENT,
    REASON_SPAM,
    reports_reasons_translations,
)
from udata.core.reports.models import Report
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory

from . import APITestCase


class ReportsReasonsAPITest(APITestCase):
    def test_reports_reasons_api(self):
        response = self.get(url_for("api.reports_reasons"))
        self.assert200(response)
        self.assertEqual(response.json, reports_reasons_translations())


class ReportsAPITest(APITestCase):
    def test_reports_api_create(self):
        user = UserFactory()

        illegal_dataset = DatasetFactory.create(owner=user)
        spam_dataset = DatasetFactory.create(owner=user)

        response = self.post(
            url_for("api.reports"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": illegal_dataset.id,
                },
                "message": "This is not appropriate",
                "reason": REASON_ILLEGAL_CONTENT,
            },
        )
        self.assert201(response)
        self.assertEqual(Report.objects.count(), 1)

        self.login(user)

        response = self.post(
            url_for("api.reports"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": spam_dataset.id,
                },
                "message": "This is spammy",
                "reason": REASON_SPAM,
            },
        )
        self.assert201(response)
        self.assertEqual(Report.objects.count(), 2)

        reports: list[Report] = list(Report.objects())
        self.assertEqual(Dataset, reports[0].subject.document_type)
        self.assertEqual(illegal_dataset.id, reports[0].subject.pk)
        self.assertEqual("This is not appropriate", reports[0].message)
        self.assertEqual(REASON_ILLEGAL_CONTENT, reports[0].reason)
        self.assertIsNone(reports[0].by)

        self.assertEqual(Dataset, reports[1].subject.document_type)
        self.assertEqual(spam_dataset.id, reports[1].subject.pk)
        self.assertEqual("This is spammy", reports[1].message)
        self.assertEqual(REASON_SPAM, reports[1].reason)
        self.assertEqual(user.id, reports[1].by.id)

        response = self.delete(url_for("api.dataset", dataset=illegal_dataset))
        self.assert204(response)

        reports[0].reload()
        self.assertEqual(Dataset, reports[0].subject.document_type)
        self.assertEqual(illegal_dataset.id, reports[0].subject.pk)
        self.assertEqual("This is not appropriate", reports[0].message)
        self.assertEqual(REASON_ILLEGAL_CONTENT, reports[0].reason)
        self.assertIsNone(reports[0].by)
        self.assertIsNotNone(reports[0].subject_deleted_at)

        reports[1].reload()
        self.assertEqual(Dataset, reports[1].subject.document_type)
        self.assertEqual(spam_dataset.id, reports[1].subject.pk)
        self.assertEqual("This is spammy", reports[1].message)
        self.assertEqual(REASON_SPAM, reports[1].reason)
        self.assertEqual(user.id, reports[1].by.id)
        self.assertIsNone(reports[1].subject_deleted_at)

        spam_dataset.delete()

        reports[1].reload()
        self.assertIsNotNone(reports[1].subject_deleted_at)

        # Should be logged as admin
        response = self.get(url_for("api.reports"))
        self.assert403(response)

        self.login(AdminFactory())
        response = self.get(url_for("api.reports"))
        self.assert200(response)

        reports = response.json["data"]
        self.assertEqual(len(reports), 2)

        self.assertEqual("Dataset", reports[0]["subject"]["class"])
        self.assertEqual(str(illegal_dataset.id), reports[0]["subject"]["id"])
        self.assertEqual("This is not appropriate", reports[0]["message"])
        self.assertEqual(REASON_ILLEGAL_CONTENT, reports[0]["reason"])
        self.assertIsNone(reports[0]["by"])
        self.assertIsNotNone(reports[0]["subject_deleted_at"])

        self.assertEqual("Dataset", reports[1]["subject"]["class"])
        self.assertEqual(str(spam_dataset.id), reports[1]["subject"]["id"])
        self.assertEqual("This is spammy", reports[1]["message"])
        self.assertEqual(REASON_SPAM, reports[1]["reason"])
        self.assertEqual(str(user.id), reports[1]["by"]["id"])
        self.assertIsNotNone(reports[1]["subject_deleted_at"])

    def test_reports_api_list(self):
        user = UserFactory()

        spam_dataset = DatasetFactory.create(owner=user)
        spam_reuse = ReuseFactory.create(owner=user)

        Report(subject=spam_dataset, reason="spam").save()
        Report(subject=spam_reuse, reason="spam").save()

        # Should be logged as admin
        response = self.get(url_for("api.reports"))
        self.assert401(response)

        self.login(AdminFactory())
        response = self.get(url_for("api.reports"))
        self.assert200(response)

        payload = response.json
        self.assertEqual(payload["total"], 2)
        # Returned by order of creation by default
        self.assertEqual(payload["data"][0]["subject"]["id"], str(spam_dataset.id))
        self.assertEqual(
            payload["data"][0]["self_api_url"],
            url_for("api.report", report=payload["data"][0]["id"], _external=True),
        )

        self.assertEqual(payload["data"][1]["subject"]["id"], str(spam_reuse.id))

    def test_reports_api_list_sort_by_reported_at(self):
        user = UserFactory()

        dataset1 = DatasetFactory.create(owner=user)
        dataset2 = DatasetFactory.create(owner=user)
        dataset3 = DatasetFactory.create(owner=user)

        # Create reports with different reported_at times
        report1 = Report(subject=dataset1, reason="spam", reported_at=datetime(2024, 1, 1)).save()
        report2 = Report(subject=dataset2, reason="spam", reported_at=datetime(2024, 1, 3)).save()
        report3 = Report(subject=dataset3, reason="spam", reported_at=datetime(2024, 1, 2)).save()

        self.login(AdminFactory())

        # Sort by -reported_at (most recent first)
        response = self.get(url_for("api.reports", sort="-reported_at"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["data"][0]["id"], str(report2.id))
        self.assertEqual(payload["data"][1]["id"], str(report3.id))
        self.assertEqual(payload["data"][2]["id"], str(report1.id))

    def test_reports_api_get(self):
        user = UserFactory()

        spam_dataset = DatasetFactory.create(owner=user)

        report = Report(subject=spam_dataset, reason="spam").save()

        # Should be logged as admin
        response = self.get(url_for("api.report", report=report))
        self.assert401(response)

        self.login(AdminFactory())
        response = self.get(url_for("api.report", report=report))
        self.assert200(response)

        payload = response.json
        self.assertEqual(payload["subject"]["id"], str(spam_dataset.id))

    def test_reports_api_dismiss(self):
        user = UserFactory()
        admin = AdminFactory()

        spam_dataset = DatasetFactory.create(owner=user)
        report = Report(subject=spam_dataset, reason="spam").save()

        dismiss_time = datetime.utcnow().isoformat()

        # Should require admin
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": dismiss_time})
        self.assert401(response)

        self.login(user)
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": dismiss_time})
        self.assert403(response)

        self.login(admin)
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": dismiss_time})
        self.assert200(response)

        payload = response.json
        self.assertIsNotNone(payload["dismissed_at"])
        self.assertEqual(payload["dismissed_by"]["id"], str(admin.id))

        report.reload()
        self.assertIsNotNone(report.dismissed_at)
        self.assertEqual(report.dismissed_by.id, admin.id)

    def test_reports_api_undismiss(self):
        user = UserFactory()
        admin = AdminFactory()

        spam_dataset = DatasetFactory.create(owner=user)
        report = Report(
            subject=spam_dataset,
            reason="spam",
            dismissed_at=datetime.utcnow(),
            dismissed_by=admin,
        ).save()

        # Verify report is dismissed
        self.assertIsNotNone(report.dismissed_at)
        self.assertIsNotNone(report.dismissed_by)

        # Should require admin
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": None})
        self.assert401(response)

        self.login(user)
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": None})
        self.assert403(response)

        self.login(admin)
        response = self.patch(url_for("api.report", report=report), {"dismissed_at": None})
        self.assert200(response)

        payload = response.json
        self.assertIsNone(payload["dismissed_at"])
        self.assertIsNone(payload["dismissed_by"])

        report.reload()
        self.assertIsNone(report.dismissed_at)
        self.assertIsNone(report.dismissed_by)

    def test_reports_api_filter_by_handled(self):
        user = UserFactory()
        admin = AdminFactory()

        dataset1 = DatasetFactory.create(owner=user)
        dataset2 = DatasetFactory.create(owner=user)

        # Unhandled report (not dismissed)
        ongoing_report = Report(subject=dataset1, reason="spam").save()

        # Handled report (dismissed)
        dismissed_report = Report(
            subject=dataset2, reason="spam", dismissed_at=datetime.utcnow(), dismissed_by=admin
        ).save()

        self.login(admin)

        # Filter by unhandled
        response = self.get(url_for("api.reports", handled="false"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["id"], str(ongoing_report.id))

        # Filter by handled
        response = self.get(url_for("api.reports", handled="true"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["id"], str(dismissed_report.id))

        # No filter (all reports)
        response = self.get(url_for("api.reports"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["total"], 2)

    def test_reports_api_filter_handled_with_deleted_subject(self):
        """Reports with deleted subjects should appear when handled="true", not handled="false"."""
        user = UserFactory()
        admin = AdminFactory()

        dataset1 = DatasetFactory.create(owner=user)
        dataset2 = DatasetFactory.create(owner=user)

        # Unhandled report (not dismissed, subject exists)
        ongoing_report = Report(subject=dataset1, reason="spam").save()

        # Report with deleted subject (should appear in "handled", not "unhandled")
        deleted_subject_report = Report(subject=dataset2, reason="spam").save()
        dataset2.delete()

        self.login(admin)

        # Filter by unhandled - should only return the report with existing subject
        response = self.get(url_for("api.reports", handled="false"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["id"], str(ongoing_report.id))

        # Filter by handled - should return the report with deleted subject
        response = self.get(url_for("api.reports", handled="true"))
        self.assert200(response)
        payload = response.json
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["id"], str(deleted_subject_report.id))
