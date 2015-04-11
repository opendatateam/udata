# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Reuse, FollowReuse, Follow, Member

from . import APITestCase
from ..factories import faker, ReuseFactory, DatasetFactory, AdminFactory, OrganizationFactory


class ReuseAPITest(APITestCase):
    def test_reuse_api_list(self):
        '''It should fetch a reuse list from the API'''
        with self.autoindex():
            reuses = [ReuseFactory(datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('api.reuses'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(reuses))

    def test_reuse_api_get(self):
        '''It should fetch a reuse from the API'''
        reuse = ReuseFactory()
        response = self.get(url_for('api.reuse', reuse=reuse))
        self.assert200(response)

    def test_reuse_api_create(self):
        '''It should create a reuse from the API'''
        data = ReuseFactory.attributes()
        self.login()
        response = self.post(url_for('api.reuses'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Reuse.objects.count(), 1)

        reuse = Reuse.objects.first()
        self.assertEqual(reuse.owner, self.user)
        self.assertIsNone(reuse.organization)

    def test_reuse_api_create_as_org(self):
        '''It should create a reuse as organization from the API'''
        self.login()
        data = ReuseFactory.attributes()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)
        response = self.post(url_for('api.reuses'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Reuse.objects.count(), 1)

        reuse = Reuse.objects.first()
        self.assertIsNone(reuse.owner)
        self.assertEqual(reuse.organization, org)

    def test_reuse_api_create_as_permissions(self):
        '''It should create a reuse as organization from the API only if user is member'''
        self.login()
        data = ReuseFactory.attributes()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = self.post(url_for('api.reuses'), data)
        self.assertStatus(response, 403)
        self.assertEqual(Reuse.objects.count(), 0)

    def test_reuse_api_update(self):
        '''It should update a reuse from the API'''
        self.login()
        reuse = ReuseFactory(owner=self.user)
        data = reuse.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.reuse', reuse=reuse), data)
        self.assert200(response)
        self.assertEqual(Reuse.objects.count(), 1)
        self.assertEqual(Reuse.objects.first().description, 'new description')

    def test_reuse_api_delete(self):
        '''It should delete a reuse from the API'''
        self.login()
        reuse = ReuseFactory(owner=self.user)
        with self.api_user():
            response = self.delete(url_for('api.reuse', reuse=reuse))
        self.assertStatus(response, 204)
        self.assertEqual(Reuse.objects.count(), 1)
        self.assertIsNotNone(Reuse.objects[0].deleted)

    def test_reuse_api_feature(self):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=False)

        with self.api_user(AdminFactory()):
            response = self.post(url_for('api.reuse_featured', reuse=reuse))
        self.assert200(response)

        reuse.reload()
        self.assertTrue(reuse.featured)

    def test_reuse_api_feature_already(self):
        '''It shouldn't do anything to feature an already featured reuse'''
        reuse = ReuseFactory(featured=True)

        with self.api_user(AdminFactory()):
            response = self.post(url_for('api.reuse_featured', reuse=reuse))
        self.assert200(response)

        reuse.reload()
        self.assertTrue(reuse.featured)

    def test_reuse_api_unfeature(self):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=True)

        with self.api_user(AdminFactory()):
            response = self.delete(url_for('api.reuse_featured', reuse=reuse))
        self.assert200(response)

        reuse.reload()
        self.assertFalse(reuse.featured)

    def test_reuse_api_unfeature_already(self):
        '''It shouldn't do anything to unfeature a not featured reuse'''
        reuse = ReuseFactory(featured=False)

        with self.api_user(AdminFactory()):
            response = self.delete(url_for('api.reuse_featured', reuse=reuse))
        self.assert200(response)

        reuse.reload()
        self.assertFalse(reuse.featured)

    def test_follow_reuse(self):
        '''It should follow a reuse on POST'''
        user = self.login()
        to_follow = ReuseFactory()

        response = self.post(url_for('api.reuse_followers', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), FollowReuse)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_reuse(self):
        '''It should unfollow the reuse on DELETE'''
        user = self.login()
        to_follow = ReuseFactory()
        FollowReuse.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.reuse_followers', id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_reuses_api(self):
        '''It should suggest reuses'''
        with self.autoindex():
            for i in range(4):
                ReuseFactory(title='test-{0}'.format(i) if i % 2 else faker.word(), datasets=[DatasetFactory()])

        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_reuses_api_unicode(self):
        '''It should suggest reuses with special characters'''
        with self.autoindex():
            for i in range(4):
                ReuseFactory(title='testé-{0}'.format(i) if i % 2 else faker.word(), datasets=[DatasetFactory()])

        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_reuses_api_no_match(self):
        '''It should not provide reuse suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                ReuseFactory(datasets=[DatasetFactory()])

        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_reuses_api_empty(self):
        '''It should not provide reuse suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)
