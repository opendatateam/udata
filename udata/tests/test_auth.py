# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests.frontend import FrontTestCase


class AuthTest(FrontTestCase):
    def test_redirect_authenticated_users_to_https_if_USE_SSL(self):
        '''Should force connected user on https if USE_SSL=True'''
        self.app.config['USE_SSL'] = True
        self.login()
        response = self.get('/en/')
        self.assertStatus(response, 302)
        self.assertEqual(response.location, 'https://localhost/en/')

    def test_dont_redirect_authenticated_users_to_https_if_not_USE_SSL(self):
        '''Should not force connected user on https if USE_SSL=False'''
        self.app.config['USE_SSL'] = False
        self.login()
        response = self.get('/en/')
        self.assert200(response)
