# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.core.badges.factories import badge_factory
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import AdminFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.models import Reuse, Follow, Member, REUSE_TYPES
from udata.utils import faker

from . import APITestCase


class ReuseAPITest(APITestCase):
    modules = ['core.dataset', 'core.reuse', 'core.user', 'core.organization']

    def test_reuse_api_list(self):
        '''It should fetch a reuse list from the API'''
        with self.autoindex():
            reuses = [ReuseFactory(
                datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('api.reuses'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(reuses))

    def test_reuse_api_get(self):
        '''It should fetch a reuse from the API'''
        reuse = ReuseFactory()
        response = self.get(url_for('api.reuse', reuse=reuse))
        self.assert200(response)

    def test_reuse_api_get_deleted(self):
        '''It should not fetch a deleted reuse from the API and raise 410'''
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.get(url_for('api.reuse', reuse=reuse))
        self.assert410(response)

    def test_reuse_api_get_deleted_but_authorized(self):
        '''It should fetch a deleted reuse from the API if authorized'''
        self.login()
        reuse = ReuseFactory(deleted=datetime.now(), owner=self.user)
        response = self.get(url_for('api.reuse', reuse=reuse))
        self.assert200(response)

    def test_reuse_api_create(self):
        '''It should create a reuse from the API'''
        data = ReuseFactory.as_dict()
        self.login()
        response = self.post(url_for('api.reuses'), data)
        self.assert201(response)
        self.assertEqual(Reuse.objects.count(), 1)

        reuse = Reuse.objects.first()
        self.assertEqual(reuse.owner, self.user)
        self.assertIsNone(reuse.organization)

    def test_reuse_api_create_as_org(self):
        '''It should create a reuse as organization from the API'''
        self.login()
        data = ReuseFactory.as_dict()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)
        response = self.post(url_for('api.reuses'), data)
        self.assert201(response)
        self.assertEqual(Reuse.objects.count(), 1)

        reuse = Reuse.objects.first()
        self.assertIsNone(reuse.owner)
        self.assertEqual(reuse.organization, org)

    def test_reuse_api_create_as_permissions(self):
        """It should create a reuse as organization from the API

        only if user is member.
        """
        self.login()
        data = ReuseFactory.as_dict()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = self.post(url_for('api.reuses'), data)
        self.assert400(response)
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

    def test_reuse_api_update_deleted(self):
        '''It should not update a deleted reuse from the API and raise 410'''
        self.login()
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.put(url_for('api.reuse', reuse=reuse), {})
        self.assert410(response)

    def test_reuse_api_delete(self):
        '''It should delete a reuse from the API'''
        self.login()
        reuse = ReuseFactory(owner=self.user)
        response = self.delete(url_for('api.reuse', reuse=reuse))
        self.assertStatus(response, 204)
        self.assertEqual(Reuse.objects.count(), 1)
        self.assertIsNotNone(Reuse.objects[0].deleted)

    def test_reuse_api_delete_deleted(self):
        '''It should not delete a deleted reuse from the API and raise 410'''
        self.login()
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.delete(url_for('api.reuse', reuse=reuse))
        self.assert410(response)

    def test_reuse_api_add_dataset(self):
        '''It should add a dataset to a reuse from the API'''
        self.login()
        reuse = ReuseFactory(owner=self.user)

        dataset = DatasetFactory()
        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = self.post(url, data)
        self.assert201(response)
        reuse.reload()
        self.assertEqual(len(reuse.datasets), 1)
        self.assertEqual(reuse.datasets[-1], dataset)

        dataset = DatasetFactory()
        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = self.post(url, data)
        self.assert201(response)
        reuse.reload()
        self.assertEqual(len(reuse.datasets), 2)
        self.assertEqual(reuse.datasets[-1], dataset)

    def test_reuse_api_add_dataset_twice(self):
        '''It should not add twice a dataset to a reuse from the API'''
        self.login()
        dataset = DatasetFactory()
        reuse = ReuseFactory(owner=self.user, datasets=[dataset])

        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = self.post(url, data)
        self.assert200(response)
        reuse.reload()
        self.assertEqual(len(reuse.datasets), 1)
        self.assertEqual(reuse.datasets[-1], dataset)

    def test_reuse_api_add_dataset_not_found(self):
        '''It should return 404 when adding an unknown dataset to a reuse'''
        self.login()
        reuse = ReuseFactory(owner=self.user)

        data = {'id': 'not-found', 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = self.post(url, data)

        self.assert404(response)
        reuse.reload()
        self.assertEqual(len(reuse.datasets), 0)

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
        self.assert201(response)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        follow = Follow.objects.followers(to_follow).first()
        self.assertIsInstance(follow.following, Reuse)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_reuse(self):
        '''It should unfollow the reuse on DELETE'''
        user = self.login()
        to_follow = ReuseFactory()
        Follow.objects.create(follower=user, following=to_follow)

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
                ReuseFactory(
                    title='test-{0}'.format(i) if i % 2 else faker.word(),
                    datasets=[DatasetFactory()])

        response = self.get(url_for('api.suggest_reuses'),
                            qs={'q': 'tes', 'size': '5'})
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
                ReuseFactory(
                    title='testé-{0}'.format(i) if i % 2 else faker.word(),
                    datasets=[DatasetFactory()])

        response = self.get(url_for('api.suggest_reuses'),
                            qs={'q': 'testé', 'size': '5'})
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

        response = self.get(url_for('api.suggest_reuses'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_reuses_api_empty(self):
        '''It should not provide reuse suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_reuses'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)


class ReuseBadgeAPITest(APITestCase):
    @classmethod
    def setUpClass(cls):
        # Register at least two badges
        Reuse.__badges__['test-1'] = 'Test 1'
        Reuse.__badges__['test-2'] = 'Test 2'

        cls.factory = badge_factory(Reuse)

    def setUp(self):
        self.login(AdminFactory())
        self.reuse = ReuseFactory()

    def test_list(self):
        response = self.get(url_for('api.available_reuse_badges'))
        self.assertStatus(response, 200)
        self.assertEqual(len(response.json), len(Reuse.__badges__))
        for kind, label in Reuse.__badges__.items():
            self.assertIn(kind, response.json)
            self.assertEqual(response.json[kind], label)

    def test_create(self):
        data = self.factory.as_dict()
        with self.api_user():
            response = self.post(
                url_for('api.reuse_badges', reuse=self.reuse), data)
        self.assert201(response)
        self.reuse.reload()
        self.assertEqual(len(self.reuse.badges), 1)

    def test_create_same(self):
        data = self.factory.as_dict()
        with self.api_user():
            self.post(
                url_for('api.reuse_badges', reuse=self.reuse), data)
            response = self.post(
                url_for('api.reuse_badges', reuse=self.reuse), data)
        self.assertStatus(response, 200)
        self.reuse.reload()
        self.assertEqual(len(self.reuse.badges), 1)

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = Reuse.__badges__.keys()
        self.reuse.badges.append(
            self.factory(kind=kinds_keys[0]))
        self.reuse.save()
        data = self.factory.as_dict()
        data['kind'] = kinds_keys[1]
        with self.api_user():
            response = self.post(
                url_for('api.reuse_badges', reuse=self.reuse), data)
        self.assert201(response)
        self.reuse.reload()
        self.assertEqual(len(self.reuse.badges), 2)

    def test_delete(self):
        badge = self.factory()
        self.reuse.badges.append(badge)
        self.reuse.save()
        with self.api_user():
            response = self.delete(
                url_for('api.reuse_badge', reuse=self.reuse,
                        badge_kind=str(badge.kind)))
        self.assertStatus(response, 204)
        self.reuse.reload()
        self.assertEqual(len(self.reuse.badges), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(
                url_for('api.reuse_badge', reuse=self.reuse,
                        badge_kind=str(self.factory().kind)))
        self.assert404(response)


class ReuseReferencesAPITest(APITestCase):
    def test_reuse_types_list(self):
        '''It should fetch the reuse types list from the API'''
        response = self.get(url_for('api.reuse_types'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(REUSE_TYPES))
