import logging

import pytest
from mongoengine.fields import StringField

from udata.mongo.document import UDataDocument as Document
from udata.tests import TestCase

from ..constants import POTENTIAL_SPAM
from ..models import SpamMixin

log = logging.getLogger(__name__)


class TestModel(SpamMixin, Document):
    text = StringField(required=True)
    _created = True

    def texts_to_check_for_spam(self):
        return [self.text]


class SpamTest(TestCase):
    @pytest.mark.options(SPAM_WORDS=["spam"], SPAM_ALLOWED_LANGS=["fr"])
    def test_uppercase_lang_detect(self):
        model = TestModel(text="DONNEES DE RECENSEMENT - MARCHES PUBLICS")
        model.detect_spam()
        self.assertNotEqual(model.spam.status, POTENTIAL_SPAM)
