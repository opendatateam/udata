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
        self.assertEqual(response.json['email'], self.user.email)

    def test_get_profile_401(self):
        '''It should raise a 401 on GET /me if no user is authenticated'''
        response = self.get(url_for('api.me'))
        self.assert401(response)

    def test_update_profile(self):
        '''It should update a dataset from the API'''
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
