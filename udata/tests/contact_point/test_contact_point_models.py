import pytest

from udata.core.contact_point.factories import ContactPointFactory
from udata.models import db


@pytest.mark.usefixtures("clean_db")
class ContactPointTest:
    def test_validate_contact_role_needs_email_or_contact_form(self):
        with pytest.raises(db.ValidationError):
            ContactPointFactory(role="contact", email=None, contact_form=None)
        # The ContactPointFactory provides an email by default, so the following should not raise.
        ContactPointFactory(role="contact", contact_form=None)
        # The ContactPointFactory provides a contact_form by default, so the following should not raise.
        ContactPointFactory(role="contact", email=None)

    def test_validate_other_role_doesnt_need_an_email_or_contact_form(self):
        ContactPointFactory(role="creator", email=None, contact_form=None)
        ContactPointFactory(role="publisher", email=None, contact_form=None)
