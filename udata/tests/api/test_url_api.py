# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest

from flask import url_for

from . import APITestCase


class CheckUrlAPITest(APITestCase):

    def setUp(self):
        # If you set up a Croquemort URL, don't forget to clean up the
        # Redis database after each test. Otherwise the test against the
        # delayed URL will not pass (existing entry already fetched).
        self.CROQUEMORT_URL = self.create_app().config.get('CROQUEMORT_URL')
        if self.CROQUEMORT_URL is None:
            raise unittest.SkipTest

    def test_returned_metadata(self):
        url = 'https://www.data.gouv.fr/fr/'
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assert200(response)
        self.assertEqual(response.json['status'], '200')
        self.assertEqual(response.json['url'], url)
        self.assertEqual(response.json['content-type'],
                         'text/html; charset=utf-8')

    def test_invalid_url(self):
        url = 'https://bad.data.gouv.fr/'
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assertStatus(response, 500)
        self.assertEqual(response.json['status'], '503')

    def test_delayed_url(self):
        url = 'http://httpbin.org/delay/10'
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assertStatus(response, 502)
        self.assertEqual(
            response.json['error'],
            'We were unable to retrieve the URL after 10 attempts.')
