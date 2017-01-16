# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, API

from . import APITestCase

ns = api.namespace('fake', 'A Fake namespace')


@ns.route('/options', endpoint='fake-options')
class FakeAPI(API):
    def get(self):
        return {'success': True}


class APIAuthTest(APITestCase):
    def test_should_allow_options_and_cors(self):
        '''Should allow OPTIONS operation and give cors parameters'''
        response = self.client.options(url_for('api.fake-options'))

        self.assert200(response)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        allowed_methods = response.headers['Access-Control-Allow-Methods']
        self.assertIn('HEAD', allowed_methods)
        self.assertIn('OPTIONS', allowed_methods)
        self.assertIn('GET', allowed_methods)
