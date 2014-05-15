# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Follow, FollowOrg, FollowReuse, FollowDataset

from . import APITestCase
from ..factories import UserFactory, OrganizationFactory, DatasetFactory, ReuseFactory


class FollowAPITest(APITestCase):
    def test_follow_user(self):
        '''It should follow an user on POST'''
        user = self.login()
        to_follow = UserFactory()

        response = self.post(url_for('api.follow_user', id=to_follow.id))
        self.assertStatus(response, 201)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)
        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), Follow)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_org(self):
        '''It should follow an org on POST'''
        user = self.login()
        to_follow = OrganizationFactory()

        response = self.post(url_for('api.follow_organization', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), FollowOrg)
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
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), FollowDataset)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)


    def test_follow_reuse(self):
        '''It should follow a reuse on POST'''
        user = self.login()
        to_follow = ReuseFactory()

        response = self.post(url_for('api.follow_reuse', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), FollowReuse)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_already_followed(self):
        '''It shouldn't do anything when following an already followed user'''
        user = self.login()
        to_follow = UserFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.post(url_for('api.follow_user', id=to_follow.id))
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

        response = self.delete(url_for('api.follow_user', id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_not_existing(self):
        '''It should raise 404 when trying to unfollow someone not followed'''
        self.login()
        to_follow = UserFactory()

        response = self.delete(url_for('api.follow_user', id=to_follow.id))
        self.assert404(response)
