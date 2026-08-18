import pytest
from mongoengine.errors import ValidationError

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyDBTestCase


class ContactPointOwnershipTest(PytestOnlyDBTestCase):
    """A contact point belongs to an owner, and so must the objects referencing it."""

    def test_dataset_rejects_a_contact_point_of_another_organization(self):
        contact_point = ContactPointFactory(organization=OrganizationFactory())

        with pytest.raises(ValidationError):
            DatasetFactory(organization=OrganizationFactory(), contact_points=[contact_point])

    def test_dataset_rejects_a_contact_point_of_a_user(self):
        contact_point = ContactPointFactory(owner=UserFactory())

        with pytest.raises(ValidationError):
            DatasetFactory(organization=OrganizationFactory(), contact_points=[contact_point])

    def test_dataservice_rejects_a_contact_point_of_another_organization(self):
        contact_point = ContactPointFactory(organization=OrganizationFactory())

        with pytest.raises(ValidationError):
            DataserviceFactory(organization=OrganizationFactory(), contact_points=[contact_point])

    def test_own_contact_point_is_accepted(self):
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org)

        DatasetFactory(organization=org, contact_points=[contact_point])
        DataserviceFactory(organization=org, contact_points=[contact_point])

    def test_for_owner_reuses_an_existing_equivalent(self):
        org = OrganizationFactory()
        contact_point = ContactPointFactory(owner=UserFactory())
        existing = ContactPointFactory(
            organization=org,
            name=contact_point.name,
            email=contact_point.email,
            contact_form=contact_point.contact_form,
            role=contact_point.role,
        )

        assert contact_point.for_owner(org) == existing


class ContactPointTest(PytestOnlyDBTestCase):
    def test_validate_contact_role_needs_email_or_contact_form(self):
        with pytest.raises(ValidationError):
            ContactPointFactory(role="contact", email=None, contact_form=None)
        # The ContactPointFactory provides an email by default, so the following should not raise.
        ContactPointFactory(role="contact", contact_form=None)
        # The ContactPointFactory provides a contact_form by default, so the following should not raise.
        ContactPointFactory(role="contact", email=None)

    def test_validate_other_role_doesnt_need_an_email_or_contact_form(self):
        ContactPointFactory(role="creator", email=None, contact_form=None)
        ContactPointFactory(role="publisher", email=None, contact_form=None)
