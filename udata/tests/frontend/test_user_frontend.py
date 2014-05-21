# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import FrontTestCase
from ..factories import UserFactory, DatasetFactory, ReuseFactory, ResourceFactory


class UserBlueprintTest(FrontTestCase):
    # def setUp(self):
    #     self.user = UserFactory()

    def test_user_list(self):
        users = [UserFactory() for _ in range(3)]
        response = self.get(url_for('users.list'))
        self.assert200(response)


    def test_render_profile(self):
        '''It should render the user profile'''
        user = UserFactory()
        response = self.get(url_for('users.show', user=user))
        self.assert200(response)

    def test_render_profile_datasets(self):
        '''It should render the user profile datasets page'''
        user = UserFactory()
        datasets = [DatasetFactory(owner=user, resources=[ResourceFactory()]) for _ in range(3)]
        for _ in range(2):
            DatasetFactory(resources=[ResourceFactory()])
        response = self.get(url_for('users.datasets', user=user))
        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_profile_reuses(self):
        '''It should render the user profile reuses page'''
        user = UserFactory()
        reuses = [ReuseFactory(owner=user, datasets=[DatasetFactory()]) for _ in range(3)]
        for _ in range(2):
            ReuseFactory(datasets=[DatasetFactory()])
        response = self.get(url_for('users.reuses', user=user))
        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), len(reuses))

    def test_not_found(self):
        '''It should raise 404 if user is not found'''
        response = self.get(url_for('users.show', user='not-found'))
        self.assert404(response)

    def test_render_user_profile_form(self):
        '''It should render the user profile form'''
        self.login()
        response = self.get(url_for('users.edit', user=self.user))
        self.assert200(response)

    def test_user_profile_form_is_protected(self):
        '''It should raise a 403 if an user try to access another user profile form'''
        user = UserFactory()
        self.login()
        response = self.get(url_for('users.edit', user=user))
        self.assert403(response)

    def test_edit(self):
        '''It should handle edit form submit and redirect on user profile page'''
        self.login()
        data = self.user.to_dict()
        data['about'] = 'bla bla bla'
        response = self.post(url_for('users.edit', user=self.user), data)

        self.user.reload()
        self.assertRedirects(response, url_for('users.show', user=self.user))
        self.assertEqual(self.user.about, 'bla bla bla')

    def test_user_activity_empty(self):
        '''It should render an empty user activity page'''
        user = UserFactory()
        response = self.get(url_for('users.activity', user=user))
        self.assert200(response)

    def test_user_starred_empty(self):
        '''It should render an empty user starred page'''
        user = UserFactory()
        response = self.get(url_for('users.starred', user=user))
        self.assert200(response)

