import pytest
from mongoengine.errors import ValidationError

from udata.core.contact_point.factories import ContactPointFactory
from udata.tests.api import PytestOnlyDBTestCase


class ContactPointTest(PytestOnlyDBTestCase):
    def test_validate_contact_role_needs_email_or_contact_form(self):
        with pytest.raises(ValidationError):
            ContactPointFactory(role="contact", email=None, contact_form=None)
        # The ContactPointFactory provides an email by default, so the following should not raise.
        ContactPointFactory(role="contact", contact_form=None)
        # The ContactPointFactory provides a contact_form by default, so the following should not raise.
        ContactPointFactory(role="contact", email=None)

    def test_a_contact_point_does_not_need_a_name(self):
        """Harvested agents often carry an email and no name at all."""
        contact_point = ContactPointFactory(name=None, role="contact")

        assert contact_point.name is None

    def test_a_contact_point_needs_a_name_an_email_or_a_contact_form(self):
        with pytest.raises(ValidationError):
            ContactPointFactory(name=None, email=None, contact_form=None, role="creator")

        ContactPointFactory(name=None, contact_form=None, role="creator")
        ContactPointFactory(email=None, contact_form=None, role="creator")

    def test_validate_other_role_doesnt_need_an_email_or_contact_form(self):
        ContactPointFactory(role="creator", email=None, contact_form=None)
        ContactPointFactory(role="publisher", email=None, contact_form=None)
