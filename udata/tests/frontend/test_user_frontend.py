# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import FrontTestCase
from ..factories import UserFactory


class UserBlueprintTest(FrontTestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_render_profile(self):
        '''It should render the user profile'''
        response = self.get(url_for('users.show', user=self.user))
        self.assert200(response)

    def test_not_found(self):
        '''It should raise 404 if user is not found'''
        response = self.get(url_for('users.show', user='not-found'))
        self.assert404(response)

    def test_render_user_profile_form(self):
        '''It should render the user profile form'''
        response = self.get(url_for('users.edit', user=self.user))
        self.assert200(response)

    def test_edit(self):
        '''It should handle edit form submit and redirect on user profile page'''
        data = self.user.to_dict()
        data['about'] = 'bla bla bla'
        self.login()
        response = self.post(url_for('users.edit', user=self.user), data)

        self.user.reload()
        self.assertRedirects(response, url_for('users.show', user=self.user))
        self.assertEqual(self.user.about, 'bla bla bla')

    def test_user_activity_empty(self):
        '''It should render an empty user activity page'''
        response = self.get(url_for('users.activity', user=self.user))
        self.assert200(response)

    def test_user_starred_empty(self):
        '''It should render an empty user starred page'''
        response = self.get(url_for('users.starred', user=self.user))
        self.assert200(response)

