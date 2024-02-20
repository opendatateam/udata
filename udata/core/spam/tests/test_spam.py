import logging
import pytest
from udata.tests import TestCase
from udata.tests.helpers import assert_not_emit
from udata.models import db

from ..models import POTENTIAL_SPAM, SpamMixin


log = logging.getLogger(__name__)

class TestModel(SpamMixin, db.Document):
    text = db.StringField(required=True)
    _created = True

    def texts_to_check_for_spam(self):
        return [self.text]


class SpamTest(TestCase):
    @pytest.mark.options(SPAM_WORDS=['spam'], SPAM_ALLOWED_LANGS=['fr'])
    def test_uppercase_lang_detect(self):
        model = TestModel(text="DONNEES DE RECENSEMENT - MARCHES PUBLICS")
        model.detect_spam()
        self.assertNotEqual(model.spam.status, POTENTIAL_SPAM)

