import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.models import Discussion, Message
from udata.core.reports.constants import REASON_AUTO_SPAM
from udata.core.reports.models import Report
from udata.core.user.factories import UserFactory
from udata.tests.api import APITestCase


class SpamTest(APITestCase):
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

        self.assertFalse(discussion.is_spam())
        self.assertEqual(Report.objects(reason=REASON_AUTO_SPAM).count(), 0)

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

        self.assertTrue(discussion.is_spam())
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

        self.assertFalse(discussion.is_spam())
        self.assertEqual(Report.objects(reason=REASON_AUTO_SPAM).count(), 0)
