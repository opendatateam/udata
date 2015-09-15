# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import User

from udata.tests.factories import ReuseFactory

from . import APITestCase


class MeAPITest(APITestCase):
    def test_get_profile(self):
        '''It should fetch my user data on GET'''
        self.login()
        response = self.get(url_for('api.me'))
        self.assert200(response)
        # self.assertEqual(response.json['email'], self.user.email)
        self.assertEqual(response.json['first_name'], self.user.first_name)
        self.assertEqual(response.json['roles'], [])

    def test_get_profile_401(self):
        '''It should raise a 401 on GET /me if no user is authenticated'''
        response = self.get(url_for('api.me'))
        self.assert401(response)

    def test_update_profile(self):
        '''It should update my profile from the API'''
        self.login()
        data = self.user.to_dict()
        data['about'] = 'new about'
        response = self.put(url_for('api.me'), data)
        self.assert200(response)
        self.assertEqual(User.objects.count(), 1)
        self.user.reload()
        self.assertEqual(self.user.about, 'new about')

    def test_my_reuses(self):
        user = self.login()
        reuses = [ReuseFactory(owner=user) for _ in range(3)]

        response = self.get(url_for('api.my_reuses'))
        self.assert200(response)

        self.assertEqual(len(response.json), len(reuses))

    def test_my_reuses_401(self):
        response = self.get(url_for('api.my_reuses'))
        self.assert401(response)

    def test_generate_apikey(self):
        '''It should generate an API Key on POST'''
        self.login()
        response = self.post(url_for('api.my_apikey'))
        self.assert201(response)
        self.assertIsNotNone(response.json['apikey'])

        self.user.reload()
        self.assertIsNotNone(self.user.apikey)
        self.assertEqual(self.user.apikey, response.json['apikey'])

    def test_regenerate_apikey(self):
        '''It should regenerate an API Key on POST'''
        self.login()
        self.user.generate_api_key()
        self.user.save()

        apikey = self.user.apikey
        response = self.post(url_for('api.my_apikey'))
        self.assert201(response)
        self.assertIsNotNone(response.json['apikey'])

        self.user.reload()
        self.assertIsNotNone(self.user.apikey)
        self.assertNotEqual(self.user.apikey, apikey)
        self.assertEqual(self.user.apikey, response.json['apikey'])

    def test_clear_apikey(self):
        '''It should clear an API Key on DELETE'''
        self.login()
        self.user.generate_api_key()
        self.user.save()

        response = self.delete(url_for('api.my_apikey'))
        self.assert204(response)

        self.user.reload()
        self.assertIsNone(self.user.apikey)
