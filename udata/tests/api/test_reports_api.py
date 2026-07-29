from datetime import UTC, datetime

from bson import DBRef
from flask import url_for

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion, Message
from udata.core.reports.constants import (
    REASON_AUTO_SPAM,
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
        self.assertEqual(illegal_dataset.title, reports[0].subject_label)

        self.assertEqual(Dataset, reports[1].subject.document_type)
        self.assertEqual(spam_dataset.id, reports[1].subject.pk)
        self.assertEqual("This is spammy", reports[1].message)
        self.assertEqual(REASON_SPAM, reports[1].reason)
        self.assertEqual(user.id, reports[1].by.id)
        self.assertEqual(spam_dataset.title, reports[1].subject_label)

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

    def test_reports_api_create_with_user_subject(self):
        user = UserFactory()

        response = self.post(
            url_for("api.reports"),
            {
                "subject": {
                    "class": "User",
                    "id": user.id,
                },
                "message": "Spam profile",
                "reason": REASON_SPAM,
            },
        )
        self.assert201(response)

        report = Report.objects.first()
        self.assertEqual(report.subject.pk, user.id)
        self.assertEqual(report.reason, REASON_SPAM)
        self.assertEqual(report.subject_label, user.slug)

    def test_reports_api_list_with_raw_dbref_subject(self):
        """Listing reports should not crash when the subject was stored as a raw DBRef
        (e.g. from the SpamInfo migration) after the fix migration has run."""
        admin = AdminFactory()

        dataset = DatasetFactory.create(owner=admin)
        message = MessageDiscussionFactory(posted_by=admin)
        discussion = DiscussionFactory.create(user=admin, subject=dataset, discussion=[message])

        Report._get_collection().insert_one(
            {
                "subject": DBRef("discussion", discussion.id),
                "reason": REASON_SPAM,
                "message": "Migrated from legacy SpamInfo",
                "reported_at": datetime.now(UTC),
            }
        )

        self.login(admin)

        # Before migration: raw DBRef causes 500
        response = self.get(url_for("api.reports"))
        self.assert500(response)

        # Run the fix migration
        from mongoengine.connection import get_db

        from udata.db.migrations import load_migration

        migration = load_migration("2026-04-01-fix-report-subject-dbref-format.py")
        migration.migrate(get_db())

        # After migration: works
        response = self.get(url_for("api.reports"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["data"][0]["subject"]["class"], "Discussion")
        self.assertEqual(response.json["data"][0]["subject"]["id"], str(discussion.id))

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

    def test_reports_api_filter_by_subject_type(self):
        user = UserFactory()

        dataset = DatasetFactory.create(owner=user)
        reuse = ReuseFactory.create(owner=user)

        Report(subject=dataset, reason=REASON_SPAM).save()
        Report(subject=reuse, reason=REASON_SPAM).save()

        self.login(AdminFactory())

        response = self.get(url_for("api.reports", subject_type="Dataset"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["data"][0]["subject"]["id"], str(dataset.id))

        response = self.get(url_for("api.reports", subject_type="Reuse"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["data"][0]["subject"]["id"], str(reuse.id))

        response = self.get(url_for("api.reports"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 2)

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

        dismiss_time = datetime.now(UTC).isoformat()

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
            dismissed_at=datetime.now(UTC),
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
            subject=dataset2, reason="spam", dismissed_at=datetime.now(UTC), dismissed_by=admin
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

    def test_reports_marked_handled_when_dataservice_soft_deleted(self):
        """Soft-deleting a Dataservice (which uses `deleted_at`) should mark its reports as handled."""
        user = UserFactory()
        admin = AdminFactory()

        dataservice = DataserviceFactory.create(owner=user)
        report = Report(subject=dataservice, reason=REASON_SPAM).save()

        report.reload()
        self.assertIsNone(report.subject_deleted_at)

        self.login(admin)

        # Soft delete the dataservice
        response = self.delete(url_for("api.dataservice", dataservice=dataservice))
        self.assert204(response)

        report.reload()
        self.assertIsNotNone(report.subject_deleted_at)

        # Report should appear as handled
        response = self.get(url_for("api.reports", handled="true"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["data"][0]["id"], str(report.id))

        # And not as unhandled
        response = self.get(url_for("api.reports", handled="false"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 0)

    def test_reports_marked_handled_when_dataset_soft_deleted(self):
        """Soft-deleting a Dataset should mark its reports as handled with deleted_by."""
        user = UserFactory()
        admin = AdminFactory()

        dataset = DatasetFactory.create(owner=user)
        report = Report(subject=dataset, reason=REASON_SPAM).save()

        self.assertIsNone(report.subject_deleted_at)

        self.login(admin)

        response = self.delete(url_for("api.dataset", dataset=dataset))
        self.assert204(response)

        report.reload()
        self.assertIsNotNone(report.subject_deleted_at)
        self.assertEqual(report.subject_deleted_by.id, admin.id)

    def test_reports_marked_handled_when_discussion_hard_deleted(self):
        """Hard-deleting a Discussion should mark its reports as handled with deleted_by."""
        user = UserFactory()
        admin = AdminFactory()

        dataset = DatasetFactory.create(owner=user)
        message = MessageDiscussionFactory(posted_by=user)
        discussion = DiscussionFactory.create(user=user, subject=dataset, discussion=[message])

        report = Report(subject=discussion, reason=REASON_SPAM).save()

        self.assertIsNone(report.subject_deleted_at)

        self.login(admin)

        response = self.delete(url_for("api.discussion", id=discussion.id))
        self.assert204(response)

        report.reload()
        self.assertIsNotNone(report.subject_deleted_at)
        self.assertEqual(report.subject_deleted_by.id, admin.id)

    def test_reports_on_message_marked_handled_when_discussion_hard_deleted(self):
        """Hard-deleting a Discussion should also mark reports on its messages as handled."""
        user = UserFactory()
        admin = AdminFactory()

        dataset = DatasetFactory.create(owner=user)
        message = MessageDiscussionFactory(posted_by=user)
        discussion = DiscussionFactory.create(user=user, subject=dataset, discussion=[message])

        report = Report(subject=discussion, subject_embed_id=message.id, reason=REASON_SPAM).save()

        self.assertIsNone(report.subject_deleted_at)

        self.login(admin)

        response = self.delete(url_for("api.discussion", id=discussion.id))
        self.assert204(response)

        report.reload()
        self.assertIsNotNone(report.subject_deleted_at)
        self.assertEqual(report.subject_deleted_by.id, admin.id)

    def test_reports_on_message_marked_handled_when_message_deleted(self):
        """Deleting a message should mark reports targeting that specific message as handled."""
        user = UserFactory()
        admin = AdminFactory()

        dataset = DatasetFactory.create(owner=user)
        first_message = MessageDiscussionFactory(posted_by=user)
        second_message = MessageDiscussionFactory(posted_by=user)
        discussion = DiscussionFactory.create(
            user=user, subject=dataset, discussion=[first_message, second_message]
        )

        report_on_message = Report(
            subject=discussion, subject_embed_id=second_message.id, reason=REASON_SPAM
        ).save()
        report_on_discussion = Report(subject=discussion, reason=REASON_SPAM).save()

        self.login(admin)

        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=1))
        self.assert204(response)

        report_on_message.reload()
        self.assertIsNotNone(report_on_message.subject_deleted_at)
        self.assertEqual(report_on_message.subject_deleted_by.id, admin.id)

        report_on_discussion.reload()
        self.assertIsNone(report_on_discussion.subject_deleted_at)
        self.assertIsNone(report_on_discussion.subject_deleted_by)

    def test_reports_api_callbacks_count_returned_in_response(self):
        """The API should return the callbacks count, not the full callbacks dict."""
        admin = AdminFactory()
        user = UserFactory()

        dataset = Dataset.objects.create(title="Test dataset", owner=user)
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="Test", discussion=[message]
        )

        report = Report(
            subject=discussion,
            reason=REASON_AUTO_SPAM,
            callbacks={"signal_new": {"args": [], "kwargs": {}}},
        ).save()

        self.login(admin)

        # GET single report — should have count, not the full dict
        response = self.get(url_for("api.report", report=report))
        self.assert200(response)
        self.assertNotIn("callbacks", response.json)
        self.assertEqual(response.json["callbacks_count"], 1)

        # GET list
        response = self.get(url_for("api.reports"))
        self.assert200(response)
        self.assertNotIn("callbacks", response.json["data"][0])
        self.assertEqual(response.json["data"][0]["callbacks_count"], 1)

        # PATCH dismiss — callbacks are executed and cleared
        response = self.patch(
            url_for("api.report", report=report),
            {"dismissed_at": datetime.now(UTC).isoformat()},
        )
        self.assert200(response)
        self.assertEqual(response.json["callbacks_count"], 0)

        report.reload()
        self.assertEqual(report.callbacks, {})
