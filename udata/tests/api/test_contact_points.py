from flask import url_for

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.contact_point.models import CONTACT_ROLES
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.i18n import gettext as _
from udata.models import ContactPoint
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert201, assert204, assert400, assert403
from udata.utils import faker


class ContactPointAPITest(APITestCase):
    def test_get_or_create(self):
        org = OrganizationFactory()
        contact_point, created = ContactPoint.objects().get_or_create(
            name="An Organization",
            email=None,
            contact_form=None,
            role="publisher",
            organization=org.id,
        )

        assert created
        assert contact_point.name == "An Organization"

        contact_point, created = ContactPoint.objects().get_or_create(
            name="An Organization",
            email=None,
            contact_form=None,
            role="publisher",
            organization=org.id,
        )
        assert not created
        assert contact_point.name == "An Organization"

        contact_point, created = ContactPoint.objects().get_or_create(
            name="Another",
            email=None,
            contact_form=None,
            role="publisher",
            organization=org.id,
        )
        assert created
        assert contact_point.name == "Another"

    def test_contact_point_api_create(self):
        user = self.login()
        data = {
            "name": faker.word(),
            "email": faker.email(),
            "contact_form": faker.url(),
            "role": "contact",
        }
        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

        contact_point = ContactPoint.objects.first()
        assert contact_point.owner.id == user.id

    def test_contact_point_api_create_email_or_contact_form(self):
        self.login()
        data = {"name": faker.word(), "contact_form": faker.url(), "role": "contact"}
        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

        data = {"name": faker.word(), "email": faker.email(), "role": "contact"}
        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 2

    def test_contact_point_duplicate_creation(self):
        self.login()
        data = {"name": faker.word(), "contact_form": faker.url(), "role": "contact"}
        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

        response = self.post(url_for("api.contact_points"), data=data)
        assert200(response)
        assert ContactPoint.objects.count() == 1

    def test_contact_point_for_different_org(self):
        user = self.login()
        member = Member(user=user, role="editor")
        org_a = OrganizationFactory(members=[member])

        data = {
            "name": faker.word(),
            "contact_form": faker.url(),
            "role": "contact",
            "organization": str(org_a.id),
        }
        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

        response = self.post(url_for("api.contact_points"), data=data)
        assert200(response)
        assert ContactPoint.objects.count() == 1

        contact_point = ContactPoint.objects.first()
        assert contact_point.owner is None
        assert contact_point.organization.id == org_a.id

        org_b = OrganizationFactory(members=[])
        data["organization"] = str(org_b.id)
        response = self.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert ContactPoint.objects.count() == 1

        org_b.members = [Member(user=user, role="editor")]
        org_b.save()

        response = self.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 2

    def test_contact_point_api_invalid_email(self):
        self.login()
        data = {"name": faker.word(), "email": faker.word(), "role": "contact"}
        response = self.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert "email" in response.json["errors"]
        assert ContactPoint.objects.count() == 0

    def test_contact_point_missing_contact_information(self):
        self.login()
        data = {"name": faker.word(), "role": "contact"}
        response = self.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert response.json["message"] == _(
            "At least an email or a contact form is required for a contact point"
        )
        assert ContactPoint.objects.count() == 0

    def test_contact_point_missing_role(self):
        self.login()
        data = {"name": faker.word(), "email": faker.email()}
        response = self.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert (
            response.json["message"]
            == "ValidationError (ContactPoint:None) (Field is required: ['role'])"
        )
        assert ContactPoint.objects.count() == 0

    def test_contact_point_no_need_for_email_for_role_other_than_contact(self):
        self.login()
        roles_other_than_contact = [role_ for role_ in CONTACT_ROLES.keys() if role_ != "contact"]
        for index, role in enumerate(roles_other_than_contact):
            data = {"name": faker.word(), "role": role}
            response = self.post(url_for("api.contact_points"), data=data)
            assert201(response)
            assert ContactPoint.objects.count() == index + 1

    def test_contact_point_api_update(self):
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        contact_point = ContactPointFactory(organization=org)
        data = contact_point.to_dict()
        data["email"] = "new.email@newdomain.com"
        response = self.put(url_for("api.contact_point", contact_point=contact_point), data)
        assert200(response)
        assert ContactPoint.objects.count() == 1
        assert ContactPoint.objects.first().email == "new.email@newdomain.com"

    def test_contact_point_api_update_to_existing_contact_point(self):
        user = self.login()
        contact_point_a = ContactPointFactory(email="a@example.org", owner=user)
        contact_point_b = ContactPointFactory(email="b@example.org", owner=user)

        data_b = contact_point_b.to_dict()
        response = self.put(url_for("api.contact_point", contact_point=contact_point_a), data_b)
        assert400(response)
        assert ContactPoint.objects.count() == 2

        contact_point_a.reload()
        assert contact_point_a.email == "a@example.org"

    def test_contact_point_api_update_forbidden(self):
        self.login()
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org)
        data = contact_point.to_dict()
        data["email"] = "new.email@newdomain.com"
        response = self.put(url_for("api.contact_point", contact_point=contact_point), data)
        assert403(response)
        assert ContactPoint.objects.count() == 1
        assert ContactPoint.objects.first().email == contact_point.email

    def test_contact_point_api_delete(self):
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        contact_point = ContactPointFactory(organization=org)
        response = self.delete(url_for("api.contact_point", contact_point=contact_point))
        assert204(response)
        assert ContactPoint.objects.count() == 0

    def test_contact_point_roles_list(self):
        """It should fetch the contact point roles list from the API"""
        response = self.get(url_for("api.contact_point_roles"))
        assert200(response)
        assert len(response.json) == len(CONTACT_ROLES)

    def test_contact_point_api_delete_forbidden(self):
        self.login()
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org)
        response = self.delete(url_for("api.contact_point", contact_point=contact_point))
        assert403(response)
        assert ContactPoint.objects.count() == 1
