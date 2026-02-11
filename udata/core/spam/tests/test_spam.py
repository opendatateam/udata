import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.models import Discussion, Message
from udata.core.reports.constants import REASON_AUTO_SPAM
from udata.core.reports.models import Report
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
        from datetime import datetime

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
