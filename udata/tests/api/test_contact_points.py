import pytest
from flask import url_for

from udata.core.contact_point.factories import ContactPointFactory
from udata.i18n import gettext as _
from udata.models import ContactPoint
from udata.tests.helpers import assert200, assert201, assert204, assert400
from udata.utils import faker

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
]


class ContactPointAPITest:
    modules = []

    def test_contact_point_api_create(self, api):
        api.login()
        data = {"name": faker.word(), "email": faker.email(), "contact_form": faker.url()}
        response = api.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

    def test_contact_point_api_create_email_or_contact_form(self, api):
        api.login()
        data = {"name": faker.word(), "contact_form": faker.url()}
        response = api.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 1

        data = {"name": faker.word(), "email": faker.email()}
        response = api.post(url_for("api.contact_points"), data=data)
        assert201(response)
        assert ContactPoint.objects.count() == 2

    def test_contact_point_api_invalid_email(self, api):
        api.login()
        data = {"name": faker.word(), "email": faker.word()}
        response = api.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert "email" in response.json["errors"]
        assert ContactPoint.objects.count() == 0

    def test_contact_point_missing_contact_information(self, api):
        api.login()
        data = {"name": faker.word()}
        response = api.post(url_for("api.contact_points"), data=data)
        assert400(response)
        assert response.json["message"] == _(
            "At least an email or a contact form is required for a contact point"
        )
        assert ContactPoint.objects.count() == 0

    def test_contact_point_api_update(self, api):
        api.login()
        contact_point = ContactPointFactory()
        data = contact_point.to_dict()
        data["email"] = "new.email@newdomain.com"
        response = api.put(url_for("api.contact_point", contact_point=contact_point), data)
        assert200(response)
        assert ContactPoint.objects.count() == 1
        assert ContactPoint.objects.first().email == "new.email@newdomain.com"

    def test_contact_point_api_delete(self, api):
        api.login()
        contact_point = ContactPointFactory()
        response = api.delete(url_for("api.contact_point", contact_point=contact_point))
        assert204(response)
        assert ContactPoint.objects.count() == 0
