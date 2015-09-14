# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Follow, FollowUser

from . import APITestCase
from ..factories import faker, UserFactory


class UserAPITest(APITestCase):
    def test_follow_user(self):
        '''It should follow an user on POST'''
        user = self.login()
        to_follow = UserFactory()

        response = self.post(url_for('api.user_followers', id=to_follow.id))
        self.assertStatus(response, 201)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)
        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(),
                              Follow)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_myself(self):
        '''It should not allow to follow myself'''
        user = self.login()

        response = self.post(url_for('api.user_followers', id=user.id))
        self.assertStatus(response, 403)

        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow(self):
        '''It should unfollow the user on DELETE'''
        user = self.login()
        to_follow = UserFactory()
        FollowUser.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.user_followers', id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_users_api_first_name(self):
        '''It should suggest users based on first name'''
        with self.autoindex():
            for i in range(4):
                UserFactory(
                    first_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('test', suggestion['first_name'])

    def test_suggest_users_api_last_name(self):
        '''It should suggest users based on last name'''
        with self.autoindex():
            for i in range(4):
                UserFactory(
                    last_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('test', suggestion['last_name'])

    def test_suggest_users_api_unicode(self):
        '''It should suggest users with special characters'''
        with self.autoindex():
            for i in range(4):
                UserFactory(
                    last_name='testé-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('test', suggestion['last_name'])

    def test_suggest_users_api_no_match(self):
        '''It should not provide user suggestion if no match'''
        with self.autoindex():
            UserFactory.create_batch(3)

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_users_api_empty(self):
        '''It should not provide user suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_users_api_no_dedup(self):
        '''It should suggest users without deduplicating homonyms'''
        with self.autoindex():
            UserFactory.create_batch(2, first_name='test', last_name='homonym')

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'homonym', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertEqual(suggestion['first_name'], 'test')
            self.assertEqual(suggestion['last_name'], 'homonym')

    def test_suggest_users_api_by_id(self):
        '''It should suggest an user based on its ID'''
        with self.autoindex():
            users = UserFactory.create_batch(4)

        user = users[0]
        response = self.get(url_for('api.suggest_users'),
                            qs={'q': str(user.id), 'size': '5'})
        self.assert200(response)

        self.assertGreaterEqual(len(response.json), 1)

        suggestion = response.json[0]
        self.assertEqual(suggestion['id'], str(user.id))
