# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import Blueprint

from udata.tests.frontend import FrontTestCase


bp = Blueprint('test_auth', __name__)


@bp.route('/empty/')
def empty():
    return ''


class AuthTest(FrontTestCase):
    def create_app(self):
        app = super(AuthTest, self).create_app()
        app.register_blueprint(bp)
        return app

    def test_redirect_authenticated_users_to_https_if_USE_SSL(self):
        '''Should force connected user on https if USE_SSL=True'''
        self.app.config['USE_SSL'] = True
        self.app.config['TESTING'] = False
        self.login()
        response = self.get('/empty/')
        self.assertStatus(response, 302)
        self.assertEqual(response.location, 'https://localhost/empty/')

    def test_dont_redirect_authenticated_users_to_https_if_not_USE_SSL(self):
        '''Should not force connected user on https if USE_SSL=False'''
        self.app.config['USE_SSL'] = False
        self.app.config['TESTING'] = False
        self.login()
        response = self.get('/empty/')
        self.assert200(response)
