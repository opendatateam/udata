# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from StringIO import StringIO

from datetime import datetime

from flask import url_for

from udata.models import (
    CommunityResource, Dataset, Follow, FollowDataset, Member,
    UPDATE_FREQUENCIES
)

from . import APITestCase
from ..factories import (
    badge_factory, faker, DatasetFactory, VisibleDatasetFactory,
    CommunityResourceFactory, ResourceFactory, OrganizationFactory,
    AdminFactory, UserFactory, LicenseFactory
)

from nose.plugins.attrib import attr


SAMPLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [
      [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],
      [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]],
       [[100.2, 0.2], [100.8, 0.2], [100.8, 0.8], [100.2, 0.8], [100.2, 0.2]]]
    ]
}


class DatasetAPITest(APITestCase):
    def test_dataset_api_list(self):
        '''It should fetch a dataset list from the API'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()])
                        for i in range(2)]

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))
        self.assertFalse('quality' in response.json['data'][0])

    def test_dataset_full_api_list(self):
        '''It should fetch a dataset list from the API'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()])
                        for i in range(2)]

        response = self.get(url_for('api.datasets_full'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))
        self.assertTrue('quality' in response.json['data'][0])

    def test_dataset_api_list_with_extra_filter(self):
        '''It should fetch a dataset list from the API filtering on extras'''
        with self.autoindex():
            for i in range(2):
                DatasetFactory(resources=[ResourceFactory()],
                               extras={'key': i})

        response = self.get(url_for('api.datasets', **{'extra.key': 1}))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['extras']['key'], 1)

    def test_dataset_api_get(self):
        '''It should fetch a dataset from the API'''
        with self.autoindex():
            resources = [ResourceFactory() for _ in range(2)]
            dataset = DatasetFactory(resources=resources)

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(len(data['resources']), len(resources))
        self.assertFalse('quality' in data)

    def test_dataset_api_get_deleted(self):
        '''It should not fetch a deleted dataset from the API and raise 410'''
        dataset = VisibleDatasetFactory(deleted=datetime.now())

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assertStatus(response, 410)

    def test_dataset_api_get_deleted_but_authorized(self):
        '''It should a deleted dataset from the API if user is authorized'''
        self.login()
        dataset = VisibleDatasetFactory(owner=self.user,
                                        deleted=datetime.now())

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)

    @attr('create')
    def test_dataset_api_create(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.attributes()
        self.login()
        response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.owner, self.user)
        self.assertIsNone(dataset.organization)

    @attr('create')
    def test_dataset_api_create_as_org(self):
        '''It should create a dataset as organization from the API'''
        self.login()
        data = DatasetFactory.attributes()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)

        response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.organization, org)
        self.assertIsNone(dataset.owner)

    @attr('create')
    def test_dataset_api_create_as_org_permissions(self):
        """It should create a dataset as organization from the API

        only if the current user is member.
        """
        self.login()
        data = DatasetFactory.attributes()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = self.post(url_for('api.datasets'), data)
        self.assert400(response)
        self.assertEqual(Dataset.objects.count(), 0)

    @attr('create')
    def test_dataset_api_create_tags(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.attributes()
        data['tags'] = [faker.word() for _ in range(3)]
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual(dataset.tags, data['tags'])

    @attr('create')
    def test_dataset_api_create_with_extras(self):
        '''It should create a dataset with extras from the API'''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    @attr('create')
    def test_dataset_api_create_with_resources(self):
        '''It should create a dataset with resources from the API'''
        data = DatasetFactory.attributes()
        data['resources'] = [ResourceFactory.attributes() for _ in range(3)]

        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(len(dataset.resources), 3)

    @attr('create')
    def test_dataset_api_create_with_geom(self):
        '''It should create a dataset with resources from the API'''
        data = DatasetFactory.attributes()
        data['spatial'] = {'geom': SAMPLE_GEOM}

        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.spatial.geom, SAMPLE_GEOM)

    def test_dataset_api_retrieve_full(self):
        '''It should retrieve a full dataset (quality) from the API.'''
        user = self.login()
        dataset = DatasetFactory(owner=user, description='')
        response = self.get(url_for('api.dataset_full', dataset=dataset))
        self.assert200(response)
        self.assertEqual(response.json['quality'], {'score': 0})
        dataset.description = 'b' * 42
        dataset.save()
        response = self.get(url_for('api.dataset_full', dataset=dataset))
        self.assertEqual(response.json['quality'], {
            'score': 0,
            'description_length': 42
        })

    @attr('update')
    def test_dataset_api_update(self):
        '''It should update a dataset from the API'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         'new description')

    @attr('update')
    def test_dataset_api_update_with_resources(self):
        '''It should update a dataset from the API with resources parameters'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user)
        initial_length = len(dataset.resources)
        data = dataset.to_dict()
        data['resources'].append(ResourceFactory.attributes())
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(len(dataset.resources), initial_length + 1)

    @attr('update')
    def test_dataset_api_update_without_resources(self):
        '''It should update a dataset from the API without resources'''
        user = self.login()
        dataset = DatasetFactory(owner=user,
                                 resources=ResourceFactory.build_batch(3))
        initial_length = len(dataset.resources)
        data = dataset.to_dict()
        del data['resources']
        data['description'] = faker.sentence()
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset.reload()
        self.assertEqual(dataset.description, data['description'])
        self.assertEqual(len(dataset.resources), initial_length)

    @attr('update')
    def test_dataset_api_update_with_extras(self):
        '''It should update a dataset from the API with extras parameters'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    @attr('update')
    def test_dataset_api_update_with_no_extras(self):
        '''It should update a dataset from the API with no extras

        In that case the extras parameters are kept.
        '''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)

        dataset = Dataset.objects.first()
        data = dataset.to_dict()
        del data['extras']
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    @attr('update')
    def test_dataset_api_update_with_empty_extras(self):
        '''It should update a dataset from the API with empty extras

        In that case the extras parameters are set to an empty dict.
        '''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)

        dataset = Dataset.objects.first()
        data = dataset.to_dict()
        data['extras'] = {}
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras, {})

    @attr('update')
    def test_dataset_api_update_deleted(self):
        '''It should not update a deleted dataset from the API and raise 401'''
        user = self.login()
        dataset = DatasetFactory(owner=user, deleted=datetime.now())
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assertStatus(response, 410)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         dataset.description)

    def test_dataset_api_delete(self):
        '''It should delete a dataset from the API'''
        user = self.login()
        with self.autoindex():
            dataset = DatasetFactory(owner=user, resources=[ResourceFactory()])
            response = self.delete(url_for('api.dataset', dataset=dataset))

        self.assertStatus(response, 204)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertIsNotNone(Dataset.objects[0].deleted)

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 0)

    def test_dataset_api_delete_deleted(self):
        '''It should delete a deleted dataset from the API and raise 410'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user, deleted=datetime.now())
        response = self.delete(url_for('api.dataset', dataset=dataset))

        self.assertStatus(response, 410)

    def test_dataset_api_feature(self):
        '''It should mark the dataset featured on POST'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=False)

        response = self.post(url_for('api.dataset_featured', dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_feature_already(self):
        '''It shouldn't do anything to feature an already featured dataset'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=True)

        response = self.post(url_for('api.dataset_featured', dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_unfeature(self):
        '''It should unmark the dataset featured on POST'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=True)

        response = self.delete(url_for('api.dataset_featured',
                                       dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)

    def test_dataset_api_unfeature_already(self):
        '''It shouldn't do anything to unfeature a not featured dataset'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=False)

        response = self.delete(url_for('api.dataset_featured',
                                       dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)


class DatasetBadgeAPITest(APITestCase):
    @classmethod
    def setUpClass(cls):
        # Register at least two badges
        Dataset.__badges__['test-1'] = 'Test 1'
        Dataset.__badges__['test-2'] = 'Test 2'

        cls.factory = badge_factory(Dataset)

    def setUp(self):
        self.login(AdminFactory())
        self.dataset = DatasetFactory(owner=UserFactory())

    def test_list(self):
        response = self.get(url_for('api.available_dataset_badges'))
        self.assertStatus(response, 200)
        self.assertEqual(len(response.json), len(Dataset.__badges__))
        for kind, label in Dataset.__badges__.items():
            self.assertIn(kind, response.json)
            self.assertEqual(response.json[kind], label)

    def test_create(self):
        data = self.factory.attributes()
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_same(self):
        data = self.factory.attributes()
        with self.api_user():
            self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 200)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = Dataset.__badges__.keys()
        self.dataset.badges.append(self.factory(kind=kinds_keys[0]))
        self.dataset.save()
        data = self.factory.attributes()
        data['kind'] = kinds_keys[1]
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 2)

    def test_delete(self):
        badge = self.factory()
        self.dataset.badges.append(badge)
        self.dataset.save()
        with self.api_user():
            response = self.delete(
                url_for('api.dataset_badge', dataset=self.dataset,
                        badge_kind=str(badge.kind)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(
                url_for('api.dataset_badge', dataset=self.dataset,
                        badge_kind=str(self.factory().kind)))
        self.assert404(response)


class DatasetResourceAPITest(APITestCase):
    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    @attr('create')
    def test_create(self):
        data = ResourceFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)

    @attr('create')
    def test_create_2nd(self):
        self.dataset.resources.append(ResourceFactory())
        self.dataset.save()

        data = ResourceFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 2)

    @attr('create')
    def test_create_with_file(self):
        '''It should create a resource from the API with a file'''
        user = self.login()
        with self.autoindex():
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(organization=org)
        response = self.post(
            url_for('api.upload_dataset_resources', dataset=dataset),
            {'file': (StringIO(b'aaa'), 'test.txt')}, json=False)
        self.assertStatus(response, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')
        response = self.put(
            url_for('api.resource', dataset=dataset, rid=data['id']), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(len(dataset.resources), 1)
        self.assertTrue(
            dataset.resources[0].url.endswith('test.txt'))

    @attr('update')
    def test_reorder(self):
        self.dataset.resources = ResourceFactory.build_batch(3)
        self.dataset.save()

        initial_order = [r.id for r in self.dataset.resources]
        expected_order = [{'id': str(id)} for id in reversed(initial_order)]

        with self.api_user():
            response = self.put(url_for('api.resources', dataset=self.dataset),
                                expected_order)
        self.assertStatus(response, 200)

        self.dataset.reload()
        self.assertEqual([str(r.id) for r in self.dataset.resources],
                         [str(r['id']) for r in expected_order])

    @attr('update')
    def test_update(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        now = datetime.now()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'published': now.isoformat(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource',
                                        dataset=self.dataset,
                                        rid=str(resource.id)), data)
        self.assert200(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)
        updated = self.dataset.resources[0]
        self.assertEqual(updated.title, data['title'])
        self.assertEqual(updated.description, data['description'])
        self.assertEqual(updated.url, data['url'])
        self.assertEqualDates(updated.published, now)

    @attr('update')
    def test_bulk_update(self):
        resources = ResourceFactory.build_batch(2)
        self.dataset.resources.extend(resources)
        self.dataset.save()
        now = datetime.now()
        ids = [r.id for r in self.dataset.resources]
        data = [{
            'id': str(id),
            'title': faker.sentence(),
            'description': faker.text(),
        } for id in ids]
        data.append({
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        })
        with self.api_user():
            response = self.put(url_for('api.resources', dataset=self.dataset),
                                data)
        self.assert200(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 3)
        for idx, id in enumerate(ids):
            resource = self.dataset.resources[idx]
            rdata = data[idx]
            self.assertEqual(str(resource.id), rdata['id'])
            self.assertEqual(resource.title, rdata['title'])
            self.assertEqual(resource.description, rdata['description'])
            self.assertIsNotNone(resource.url)
        new_resource = self.dataset.resources[-1]
        self.assertEqualDates(new_resource.published, now)

    @attr('update')
    def test_update_404(self):
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource',
                                        dataset=self.dataset,
                                        rid=str(ResourceFactory().id)), data)
        self.assert404(response)

    @attr('update')
    def test_update_with_file(self):
        '''It should update a resource from the API with a file'''
        user = self.login()
        with self.autoindex():
            resource = ResourceFactory()
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(resources=[resource], organization=org)
        response = self.post(
            url_for('api.upload_dataset_resource',
                    dataset=dataset, rid=resource.id),
            {'file': (StringIO(b'aaa'), 'test.txt')}, json=False)
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')
        response = self.put(
            url_for('api.resource', dataset=dataset, rid=data['id']), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(len(dataset.resources), 1)
        self.assertTrue(
            dataset.resources[0].url.endswith('test.txt'))

    def test_delete(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        with self.api_user():
            response = self.delete(url_for('api.resource',
                                           dataset=self.dataset,
                                           rid=str(resource.id)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(url_for('api.resource',
                                           dataset=self.dataset,
                                           rid=str(ResourceFactory().id)))
        self.assert404(response)

    def test_follow_dataset(self):
        '''It should follow a dataset on POST'''
        user = self.login()
        to_follow = DatasetFactory()

        response = self.post(url_for('api.dataset_followers', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(),
                              FollowDataset)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_dataset(self):
        '''It should unfollow the dataset on DELETE'''
        user = self.login()
        to_follow = DatasetFactory()
        FollowDataset.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.dataset_followers',
                                       id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_formats_api(self):
        '''It should suggest formats'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(format=f)
                for f in (faker.word(), faker.word(), 'test', 'test-1')
            ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        # Shortest match first.
        self.assertEqual(response.json[0]['text'], 'test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('test'))

    def test_suggest_format_api_no_match(self):
        '''It should not provide format suggestion if no match'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(format=faker.word()) for _ in range(3)
            ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_format_api_empty(self):
        '''It should not provide format suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api(self):
        '''It should suggest datasets'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    title='test-{0}'.format(i) if i % 2 else faker.word(),
                    resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_datasets_api_unicode(self):
        '''It should suggest datasets withspecial characters'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    title='testé-{0}'.format(i) if i % 2 else faker.word(),
                    resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_datasets_api_no_match(self):
        '''It should not provide dataset suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                DatasetFactory(resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api_empty(self):
        '''It should not provide dataset suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)


class DatasetReferencesAPITest(APITestCase):
    def test_dataset_licenses_list(self):
        '''It should fetch the dataset licenses list from the API'''
        licenses = LicenseFactory.create_batch(4)

        response = self.get(url_for('api.licenses'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(licenses))

    def test_dataset_frequencies_list(self):
        '''It should fetch the dataset frequencies list from the API'''
        response = self.get(url_for('api.dataset_frequencies'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(UPDATE_FREQUENCIES))


class CommunityResourceAPITest(APITestCase):

    def test_community_resource_api_get(self):
        '''It should fetch a community resource from the API'''
        with self.autoindex():
            community_resource = CommunityResourceFactory()

        response = self.get(url_for('api.community_resource',
                                    community=community_resource))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))

    def test_community_resource_api_get_from_string_id(self):
        '''It should fetch a community resource from the API'''
        with self.autoindex():
            community_resource = CommunityResourceFactory()

        response = self.get(url_for('api.community_resource',
                                    community=str(community_resource.id)))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))

    @attr('create')
    def test_community_resource_api_create(self):
        '''It should create a community resource from the API'''
        self.login()
        with self.autoindex():
            resource = ResourceFactory()
            dataset = DatasetFactory(resources=[resource])
        response = self.post(
            url_for('api.upload_community_resources', dataset=dataset),
            {'file': (StringIO(b'aaa'), 'test.txt')}, json=False)
        self.assertStatus(response, 201)
        data = json.loads(response.data)
        resource_id = data['id']
        self.assertEqual(data['title'], 'test.txt')
        response = self.put(
            url_for('api.community_resource', community=resource_id),
            data)
        self.assertStatus(response, 200)
        self.assertEqual(CommunityResource.objects.count(), 1)
        community_resource = CommunityResource.objects.first()
        self.assertEqual(community_resource.owner, self.user)
        self.assertIsNone(community_resource.organization)

    @attr('create')
    def test_community_resource_api_create_as_org(self):
        '''It should create a community resource as org from the API'''
        user = self.login()
        with self.autoindex():
            resource = ResourceFactory()
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(resources=[resource])
        response = self.post(
            url_for('api.upload_community_resources', dataset=dataset),
            {'file': (StringIO(b'aaa'), 'test.txt')}, json=False)
        self.assertStatus(response, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')
        resource_id = data['id']
        data['organization'] = str(org.id)
        response = self.put(
            url_for('api.community_resource', community=resource_id),
            data)
        self.assertStatus(response, 200)
        self.assertEqual(CommunityResource.objects.count(), 1)
        community_resource = CommunityResource.objects.first()
        self.assertEqual(community_resource.organization, org)
        self.assertIsNone(community_resource.owner)

    @attr('update')
    def test_community_resource_api_update(self):
        '''It should update a community resource from the API'''
        self.login()
        with self.autoindex():
            community_resource = CommunityResourceFactory()
        data = community_resource.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.community_resource',
                                    community=community_resource),
                            data)
        self.assert200(response)
        self.assertEqual(CommunityResource.objects.count(), 1)
        self.assertEqual(CommunityResource.objects.first().description,
                         'new description')

    @attr('update')
    def test_community_resource_api_update_with_file(self):
        '''It should update a community resource file from the API'''
        user = self.login()
        with self.autoindex():
            resource = ResourceFactory()
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(resources=[resource], organization=org)
            community_resource = CommunityResourceFactory(dataset=dataset)
        response = self.post(
            url_for('api.upload_community_resource',
                    community=community_resource),
            {'file': (StringIO(b'aaa'), 'test.txt')}, json=False)
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))
        self.assertEqual(data['title'], 'test.txt')
        data['description'] = 'new description'
        response = self.put(url_for('api.community_resource',
                                    community=community_resource),
                            data)
        self.assert200(response)
        self.assertEqual(CommunityResource.objects.count(), 1)
        self.assertEqual(CommunityResource.objects.first().description,
                         'new description')
        self.assertTrue(
            CommunityResource.objects.first().url.endswith('test.txt'))
