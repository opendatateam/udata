from flask import current_app, url_for
from flask_security.utils import hash_data

from udata.core.user.factories import AdminFactory
from udata.tests.api import APITestCase


class AuthTest(APITestCase):
    def test_change_mail(self):
        user = self.login(AdminFactory())

        new_email = "test@test.com"

        security = current_app.extensions["security"]

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for("security.confirm_change_email", token=token)

        resp = self.get(confirmation_link)
        assert resp.status_code == 302

        user.reload()
        assert user.email == new_email
