# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import FrontTestCase
from udata.models import FollowDataset, FollowOrg, FollowReuse, FollowUser
from ..factories import (
    UserFactory, DatasetFactory, ReuseFactory, ResourceFactory,
    OrganizationFactory
)


class UserBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the user list page'''
        with self.autoindex():
            users = [UserFactory() for _ in range(3)]

        response = self.get(url_for('users.list'))
        self.assert200(response)

        rendered_users = self.get_context_variable('users')
        self.assertEqual(len(rendered_users), len(users))

    def test_render_list_with_query(self):
        '''It should render the user list page with a query string'''
        with self.autoindex():
            users = [UserFactory() for i in range(2)]
            expected_users = [
                UserFactory(first_name='test'),
                UserFactory(last_name='test'),
            ]
            users.extend(expected_users)

        response = self.get(url_for('users.list'), qs={'q': 'test'})

        self.assert200(response)
        rendered_users = self.get_context_variable('users')
        self.assertEqual(len(rendered_users), 2)
        rendered_ids = [u.id for u in rendered_users]
        for user in expected_users:
            self.assertIn(user.id, rendered_ids)

    def test_render_list_empty(self):
        '''It should render the dataset list page event if empty'''
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
        datasets = [DatasetFactory(owner=user, resources=[ResourceFactory()])
                    for _ in range(3)]
        for _ in range(2):
            DatasetFactory(resources=[ResourceFactory()])
        response = self.get(url_for('users.datasets', user=user))
        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_profile_reuses(self):
        '''It should render the user profile reuses page'''
        user = UserFactory()
        reuses = [ReuseFactory(owner=user, datasets=[DatasetFactory()])
                  for _ in range(3)]
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

    def test_render_profile_followers(self):
        '''It should render the user profile followers page'''
        user = UserFactory()
        followers = [FollowUser.objects.create(follower=UserFactory(),
                                               following=user)
                     for _ in range(3)]
        response = self.get(url_for('users.followers', user=user))

        self.assert200(response)

        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

    def test_render_profile_following_empty(self):
        '''It should render an empty user profile following page'''
        user = UserFactory()
        response = self.get(url_for('users.following', user=user))
        self.assert200(response)

    def test_not_found(self):
        '''It should raise 404 if user is not found'''
        response = self.get(url_for('users.show', user='not-found'))
        self.assert404(response)
