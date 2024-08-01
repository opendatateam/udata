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
    modules = []

    def test_reports_reasons_api(self):
        response = self.get(url_for("api.reports_reasons"))
        self.assert200(response)
        self.assertEqual(response.json, reports_reasons_translations())


class ReportsAPITest(APITestCase):
    modules = []

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
