# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Follow

from . import APITestCase
from ..factories import UserFactory, OrganizationFactory, DatasetFactory


class FollowAPITest(APITestCase):
    def test_follow_user(self):
        '''It should follow an user on POST'''
        user = self.login()
        to_follow = UserFactory()

        response = self.post(url_for('api.follow', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_org(self):
        '''It should follow an org on POST'''
        user = self.login()
        to_follow = OrganizationFactory()

        response = self.post(url_for('api.follow_org', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_dataset(self):
        '''It should follow a dataset on POST'''
        user = self.login()
        to_follow = DatasetFactory()

        response = self.post(url_for('api.follow_dataset', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_already_followed(self):
        '''It shouldn't do anything when following an already followed user'''
        user = self.login()
        to_follow = UserFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.post(url_for('api.follow', id=to_follow.id))
        self.assertStatus(response, 200)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow(self):
        '''It should unfollow the user on DELETE'''
        user = self.login()
        to_follow = UserFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.follow', id=to_follow.id))
        self.assertStatus(response, 204)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_not_existing(self):
        '''It should raise 404 when trying to unfollow someone not followed'''
        self.login()
        to_follow = UserFactory()

        response = self.delete(url_for('api.follow', id=to_follow.id))
        self.assert404(response)
