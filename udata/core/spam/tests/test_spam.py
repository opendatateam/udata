from datetime import datetime

import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.models import Discussion, Message
from udata.core.organization.factories import OrganizationFactory
from udata.core.reports.constants import REASON_AUTO_SPAM
from udata.core.reports.models import Report
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.tests.api import APITestCase


class SpamTest(APITestCase):
    def has_spam_report(self, subject, subject_embed_id=None):
        return (
            Report.objects(
                subject=subject,
                reason=REASON_AUTO_SPAM,
                dismissed_at=None,
                subject_embed_id=subject_embed_id,
            ).first()
            is not None
        )

    @pytest.mark.options(SPAM_WORDS=["spam"], SPAM_ALLOWED_LANGS=["fr"])
    def test_uppercase_lang_detect(self):
        """French text should not be flagged as spam when only French is allowed."""
        user = UserFactory()
        dataset = DatasetFactory()
        message = Message(content="bla bla", posted_by=user)
        # Title is in French, should not be flagged
        discussion = Discussion(
            subject=dataset,
            user=user,
            title="DONNEES DE RECENSEMENT - MARCHES PUBLICS",
            discussion=[message],
        )
        discussion.save()

        self.assertFalse(self.has_spam_report(discussion))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_spam_word_detection(self):
        """Text containing spam words should be flagged."""
        user = UserFactory()
        dataset = DatasetFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion(
            subject=dataset,
            user=user,
            title="This is spam content",
            discussion=[message],
        )
        discussion.save()

        self.assertTrue(self.has_spam_report(discussion))
        report = Report.objects(reason=REASON_AUTO_SPAM).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.subject, discussion)

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_no_spam_word(self):
        """Text without spam words should not be flagged."""
        user = UserFactory()
        dataset = DatasetFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion(
            subject=dataset,
            user=user,
            title="This is normal content",
            discussion=[message],
        )
        discussion.save()

        self.assertFalse(self.has_spam_report(discussion))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dismissed_spam_in_embed_not_reflagged(self):
        """
        When spam is in an embedded document (Message) and the report is dismissed,
        adding a new comment should NOT create a new report for the same embed.
        """

        user = UserFactory()
        dataset = DatasetFactory()
        first_message = Message(content="bla bla", posted_by=user)
        discussion = Discussion(
            subject=dataset,
            user=user,
            title="Normal title",
            discussion=[first_message],
        )
        discussion.save()

        # Add a spam comment (this is an embed, not the main document)
        discussion.discussion.append(Message(content="this is spam", posted_by=user))
        discussion.save()

        spam_message = discussion.discussion[1]
        self.assertTrue(self.has_spam_report(discussion, spam_message.id))

        # Dismiss the report
        report = Report.objects(
            subject=discussion, reason=REASON_AUTO_SPAM, subject_embed_id=spam_message.id
        ).first()
        report.dismissed_at = datetime.utcnow()
        report.save()

        self.assertFalse(self.has_spam_report(discussion, spam_message.id))

        # Add another normal comment
        discussion.reload()
        discussion.discussion.append(Message(content="another normal comment", posted_by=user))
        discussion.save()

        # The dismissed spam embed should NOT be re-flagged
        self.assertFalse(self.has_spam_report(discussion, spam_message.id))
        # And no new report should exist for the discussion
        self.assertEqual(
            Report.objects(subject=discussion, reason=REASON_AUTO_SPAM, dismissed_at=None).count(),
            0,
        )

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_discussion_first_message_spam_rechecked_when_other_message_edited(self):
        user = UserFactory()
        dataset = DatasetFactory()
        first_message = Message(content="this is spam", posted_by=user)
        second_message = Message(content="normal comment", posted_by=user)
        discussion = Discussion(
            subject=dataset,
            user=user,
            title="Normal title",
            discussion=[first_message, second_message],
        )
        discussion.save()

        self.assertTrue(self.has_spam_report(discussion))

        report = Report.objects(subject=discussion, reason=REASON_AUTO_SPAM).first()
        report.delete()

        # Editing the second message should trigger re-check of
        # discussion.0.content because both share the "discussion" root field.
        # _get_changed_fields() returns "discussion.1.content" which must match
        # field_name "discussion.0.content" via the root field "discussion".
        discussion.reload()
        discussion.discussion[1].content = "edited comment"
        discussion.save()

        self.assertTrue(self.has_spam_report(discussion))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataset_spam_in_title(self):
        dataset = DatasetFactory(title="This is spam content")
        self.assertTrue(self.has_spam_report(dataset))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataset_spam_in_description(self):
        dataset = DatasetFactory(title="Normal title", description="Buy spam products now")
        self.assertTrue(self.has_spam_report(dataset))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataset_no_spam(self):
        dataset = DatasetFactory(title="Normal title", description="Normal description")
        self.assertFalse(self.has_spam_report(dataset))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataset_spam_not_reflagged_after_dismiss(self):

        dataset = DatasetFactory(title="This is spam content")
        self.assertTrue(self.has_spam_report(dataset))

        report = Report.objects(subject=dataset, reason=REASON_AUTO_SPAM).first()
        report.dismissed_at = datetime.utcnow()
        report.save()

        dataset.reload()
        dataset.description = "Updated description"
        dataset.save()

        self.assertFalse(self.has_spam_report(dataset))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataset_unchanged_description_not_rechecked_when_description_short_changes(self):
        dataset = DatasetFactory(title="Normal title", description="This contains spam word")
        self.assertTrue(self.has_spam_report(dataset))

        report = Report.objects(subject=dataset, reason=REASON_AUTO_SPAM).first()
        report.delete()

        dataset.reload()
        dataset.description_short = "Short summary"
        dataset.save()

        self.assertFalse(self.has_spam_report(dataset))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_reuse_spam_in_title(self):
        reuse = ReuseFactory(title="This is spam content")
        self.assertTrue(self.has_spam_report(reuse))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_reuse_spam_in_description(self):
        reuse = ReuseFactory(title="Normal title", description="Buy spam products now")
        self.assertTrue(self.has_spam_report(reuse))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_reuse_no_spam(self):
        reuse = ReuseFactory(title="Normal title", description="Normal description")
        self.assertFalse(self.has_spam_report(reuse))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_organization_spam_in_name(self):
        org = OrganizationFactory(name="Spam Organization")
        self.assertTrue(self.has_spam_report(org))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_organization_spam_in_description(self):
        org = OrganizationFactory(name="Normal Org", description="Buy spam products now")
        self.assertTrue(self.has_spam_report(org))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_organization_no_spam(self):
        org = OrganizationFactory(name="Normal Org", description="Normal description")
        self.assertFalse(self.has_spam_report(org))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataservice_spam_in_title(self):
        dataservice = DataserviceFactory(title="This is spam content")
        self.assertTrue(self.has_spam_report(dataservice))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataservice_spam_in_description(self):
        dataservice = DataserviceFactory(title="Normal title", description="Buy spam products now")
        self.assertTrue(self.has_spam_report(dataservice))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_dataservice_no_spam(self):
        dataservice = DataserviceFactory(title="Normal title", description="Normal description")
        self.assertFalse(self.has_spam_report(dataservice))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_user_spam_in_about(self):
        user = UserFactory(about="Buy spam products now")
        self.assertTrue(self.has_spam_report(user))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_user_spam_in_website(self):
        user = UserFactory(website="https://spam.example.com")
        self.assertTrue(self.has_spam_report(user))

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_user_no_spam(self):
        user = UserFactory(about="Normal bio", website="https://example.com")
        self.assertFalse(self.has_spam_report(user))
