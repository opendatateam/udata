# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import FrontTestCase
from udata.models import FollowDataset, FollowOrg, FollowReuse, FollowUser
from ..factories import UserFactory, DatasetFactory, ReuseFactory, ResourceFactory, OrganizationFactory


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

    def test_render_profile_following(self):
        '''It should render the user profile following page'''
        user = UserFactory()
        for _ in range(2):
            reuse = ReuseFactory()
            FollowReuse.objects.create(follower=user, following=reuse)
            dataset = DatasetFactory()
            FollowDataset.objects.create(follower=user, following=dataset)
            org = OrganizationFactory()
            FollowOrg.objects.create(follower=user, following=org)
            other_user = UserFactory()
            FollowUser.objects.create(follower=user, following=other_user)
        response = self.get(url_for('users.following', user=user))
        self.assert200(response)
        for name in 'datasets', 'users', 'reuses', 'organizations':
            rendered = self.get_context_variable('followed_{0}'.format(name))
            self.assertEqual(len(rendered), 2)

    def test_render_profile_following_empty(self):
        '''It should render an empty user profile following page'''
        user = UserFactory()
        response = self.get(url_for('users.following', user=user))
        self.assert200(response)

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

    def test_render_user_api_key_settings(self):
        '''It should render the user api settings page'''
        self.login()
        response = self.get(url_for('users.apikey_settings', user=self.user))
        self.assert200(response)

    def test_create_user_api_key(self):
        '''It should generate an API Key'''
        user = self.login()

        self.assertIsNone(user.apikey)

        response = self.post(url_for('users.apikey_settings', user=self.user), {'action': 'generate'})
        self.assert200(response)

        user.reload()
        self.assertIsNotNone(user.apikey)

    def test_regenerate_user_api_key(self):
        '''It should regenerate an API Key'''
        user = self.login()
        user.generate_api_key()
        user.save()
        self.assertIsNotNone(user.apikey)

        old_key = user.apikey

        response = self.post(url_for('users.apikey_settings', user=self.user), {'action': 'generate'})
        self.assert200(response)

        user.reload()
        self.assertIsNotNone(user.apikey)
        self.assertNotEqual(user.apikey, old_key)

    def test_clear_user_api_key(self):
        '''It should clear the API Key'''
        user = self.login()
        user.generate_api_key()
        user.save()
        self.assertIsNotNone(user.apikey)

        response = self.post(url_for('users.apikey_settings', user=self.user), {'action': 'clear'})
        self.assert200(response)

        user.reload()
        self.assertIsNone(user.apikey)

    def test_render_user_settings(self):
        '''It should render the user preferences page'''
        self.login()
        response = self.get(url_for('users.settings', user=self.user))
        self.assert200(response)

    def test_render_user_notifications_settings(self):
        '''It should render the user notifications settings page'''
        self.login()
        response = self.get(url_for('users.notifications_settings', user=self.user))
        self.assert200(response)

    def test_user_activity_empty(self):
        '''It should render an empty user activity page'''
        user = UserFactory()
        response = self.get(url_for('users.activity', user=user))
        self.assert200(response)
