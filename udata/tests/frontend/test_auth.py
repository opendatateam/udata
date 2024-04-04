from unittest.mock import patch
from flask import url_for, current_app, get_flashed_messages
from flask_login import current_user
from flask_security.utils import hash_data
from udata.auth.views import send_change_email_confirmation_instructions
from udata.core.user.factories import AdminFactory

from . import FrontTestCase


class AuthTest(FrontTestCase):
    modules = ['admin']

    def test_change_mail(self):
        user = self.login(AdminFactory())
        url = url_for('security.change_email')

        new_email = 'test@test.com'

        security = current_app.extensions['security']

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for('security.confirm_change_email', token=token, _external=True)

        resp = self.get(confirmation_link, follow_redirects=True)
        assert resp.status_code == 200

        user.reload()
        assert user.email == new_email
