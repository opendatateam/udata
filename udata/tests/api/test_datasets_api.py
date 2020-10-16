import json

from datetime import datetime
from io import BytesIO
from uuid import uuid4

from flask import url_for
import pytest

from . import APITestCase

from udata.app import cache
from udata.core import storages
from udata.core.dataset.factories import (
    DatasetFactory, VisibleDatasetFactory, CommunityResourceFactory,
    LicenseFactory, ResourceFactory)
from udata.core.dataset.models import ResourceMixin
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.badges.factories import badge_factory
from udata.core.organization.factories import OrganizationFactory
from udata.models import (
    CommunityResource, Dataset, Follow, Member, UPDATE_FREQUENCIES,
    LEGACY_FREQUENCIES, RESOURCE_TYPES, db
)
from udata.tags import MIN_TAG_LENGTH, MAX_TAG_LENGTH
from udata.utils import unique_string, faker
from udata.tests.helpers import assert200, assert404

SAMPLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],  # noqa
        [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]],  # noqa
        [[100.2, 0.2], [100.8, 0.2], [100.8, 0.8], [100.2, 0.8], [100.2, 0.2]]]
    ]
}


class DatasetAPITest(APITestCase):
    modules = ['core.user', 'core.dataset', 'core.organization']

    def test_dataset_api_list(self):
        '''It should fetch a dataset list from the API'''
        with self.autoindex():
            datasets = [VisibleDatasetFactory() for i in range(2)]

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))
        self.assertFalse('quality' in response.json['data'][0])

    def test_dataset_api_search(self):
        '''It should search datasets from the API'''
        with self.autoindex():
            [VisibleDatasetFactory() for i in range(2)]
            dataset = VisibleDatasetFactory(title="some spécial chars")

        response = self.get(url_for('api.datasets', q='spécial'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(dataset.id))

    def test_dataset_api_list_filtered_by_org(self):
        '''It should fetch a dataset list for a given org'''
        self.login()
        with self.autoindex():
            member = Member(user=self.user, role='editor')
            org = OrganizationFactory(members=[member])
            VisibleDatasetFactory()
            dataset_org = VisibleDatasetFactory(organization=org)

        response = self.get(url_for('api.datasets'),
                            qs={'organization': str(org.id)})
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(dataset_org.id))

    def test_dataset_api_list_filtered_by_org_with_or(self):
        '''It should fetch a dataset list for two given orgs'''
        self.login()
        with self.autoindex():
            member = Member(user=self.user, role='editor')
            org1 = OrganizationFactory(members=[member])
            org2 = OrganizationFactory(members=[member])
            VisibleDatasetFactory()
            dataset_org1 = VisibleDatasetFactory(organization=org1)
            dataset_org2 = VisibleDatasetFactory(organization=org2)

        response = self.get(
            url_for('api.datasets'),
            qs={'organization': '{0}|{1}'.format(org1.id, org2.id)})
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 2)
        returned_ids = [item['id'] for item in response.json['data']]
        self.assertIn(str(dataset_org1.id), returned_ids)
        self.assertIn(str(dataset_org2.id), returned_ids)

    def test_dataset_api_list_with_facets(self):
        '''It should fetch a dataset list from the API with facets'''
        with self.autoindex():
            for i in range(2):
                VisibleDatasetFactory(tags=['tag-{0}'.format(i)])

        response = self.get(url_for('api.datasets', **{'facets': 'tag'}))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 2)
        self.assertIn('facets', response.json)
        self.assertIn('tag', response.json['facets'])

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
        self.assert410(response)

    def test_dataset_api_get_deleted_but_authorized(self):
        '''It should a deleted dataset from the API if user is authorized'''
        self.login()
        dataset = VisibleDatasetFactory(owner=self.user,
                                        deleted=datetime.now())

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)

    def test_dataset_api_create(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.as_dict()
        self.login()
        response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.owner, self.user)
        self.assertIsNone(dataset.organization)

    def test_dataset_api_create_as_org(self):
        '''It should create a dataset as organization from the API'''
        self.login()
        data = DatasetFactory.as_dict()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)

        response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.organization, org)
        self.assertIsNone(dataset.owner)

    def test_dataset_api_create_as_org_permissions(self):
        """It should create a dataset as organization from the API

        only if the current user is member.
        """
        self.login()
        data = DatasetFactory.as_dict()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = self.post(url_for('api.datasets'), data)
        self.assert400(response)
        self.assertEqual(Dataset.objects.count(), 0)

    def test_dataset_api_create_tags(self):
        '''It should create a dataset from the API with tags'''
        data = DatasetFactory.as_dict()
        data['tags'] = [unique_string(16) for _ in range(3)]
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual(dataset.tags, sorted(data['tags']))

    def test_dataset_api_fail_to_create_too_short_tags(self):
        '''It should fail to create a dataset from the API because
        the tag is too short'''
        data = DatasetFactory.as_dict()
        data['tags'] = [unique_string(MIN_TAG_LENGTH - 1)]
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 400)

    def test_dataset_api_fail_to_create_too_long_tags(self):
        '''Should fail creating a dataset with a tag long'''
        data = DatasetFactory.as_dict()
        data['tags'] = [unique_string(MAX_TAG_LENGTH + 1)]
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 400)

    def test_dataset_api_create_and_slugify_tags(self):
        '''It should create a dataset from the API and slugify the tags'''
        data = DatasetFactory.as_dict()
        data['tags'] = [' Aaa bBB $$ $$-µ  ']
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual(dataset.tags, ['aaa-bbb-u'])

    def test_dataset_api_create_with_extras(self):
        '''It should create a dataset with extras from the API'''
        data = DatasetFactory.as_dict()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    def test_dataset_api_create_with_resources(self):
        '''It should create a dataset with resources from the API'''
        data = DatasetFactory.as_dict()
        data['resources'] = [ResourceFactory.as_dict() for _ in range(3)]

        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(len(dataset.resources), 3)

    def test_dataset_api_create_with_resources_dict(self):
        """Create a dataset w/ resources in a dict instead of list,
        should fail
        """
        data = DatasetFactory.as_dict()
        data['resources'] = {
            k: v for k, v in enumerate([
                ResourceFactory.as_dict() for _ in range(3)
            ])
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert400(response)

    def test_dataset_api_create_with_geom(self):
        '''It should create a dataset with resources from the API'''
        data = DatasetFactory.as_dict()
        data['spatial'] = {'geom': SAMPLE_GEOM}

        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.spatial.geom, SAMPLE_GEOM)

    def test_dataset_api_create_with_legacy_frequency(self):
        '''It should create a dataset from the API with a legacy frequency'''
        self.login()

        for oldFreq, newFreq in LEGACY_FREQUENCIES.items():
            data = DatasetFactory.as_dict()
            data['frequency'] = oldFreq
            response = self.post(url_for('api.datasets'), data)
            self.assert201(response)
            self.assertEqual(response.json['frequency'], newFreq)

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

    def test_dataset_api_update_with_resources(self):
        '''It should update a dataset from the API with resources parameters'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user)
        initial_length = len(dataset.resources)
        data = dataset.to_dict()
        data['resources'].append(ResourceFactory.as_dict())
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(len(dataset.resources), initial_length + 1)

    def test_dataset_api_update_new_resource_with_extras(self):
        '''It should update a dataset with a new resource with extras'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user)
        data = dataset.to_dict()
        resource_data = ResourceFactory.as_dict()
        resource_data['extras'] = {'extra:id': 'id'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        resource = next((
            r for r in dataset.resources if r.title == resource_data['title']
        ))
        self.assertEqual(resource.extras, {'extra:id': 'id'})

    def test_dataset_api_update_existing_resource_with_extras(self):
        '''It should update a dataset's existing resource with extras'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user)
        data = dataset.to_dict()
        data['resources'][0]['extras'] = {'extra:id': 'id'}
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        resource = dataset.resources[0]
        self.assertEqual(resource.extras, {'extra:id': 'id'})

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

    def test_dataset_api_update_with_no_extras(self):
        '''It should update a dataset from the API with no extras

        In that case the extras parameters are kept.
        '''
        data = DatasetFactory.as_dict()
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

    def test_dataset_api_update_with_empty_extras(self):
        '''It should update a dataset from the API with empty extras

        In that case the extras parameters are set to an empty dict.
        '''
        data = DatasetFactory.as_dict()
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

    def test_dataset_api_update_deleted(self):
        '''It should not update a deleted dataset from the API and raise 401'''
        user = self.login()
        dataset = DatasetFactory(owner=user, deleted=datetime.now())
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert410(response)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         dataset.description)

    def test_dataset_api_delete(self):
        '''It should delete a dataset from the API'''
        user = self.login()
        with self.autoindex():
            dataset = VisibleDatasetFactory(owner=user)
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

        self.assert410(response)

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
        data = self.factory.as_dict()
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_same(self):
        data = self.factory.as_dict()
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
        kinds_keys = list(Dataset.__badges__)
        self.dataset.add_badge(kinds_keys[0])
        data = self.factory.as_dict()
        data['kind'] = kinds_keys[1]
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 2)

    def test_delete(self):
        badge = self.factory()
        self.dataset.add_badge(badge.kind)
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
    modules = None

    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_get(self):
        '''It should fetch a resource from the API'''
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        response = self.get(url_for('api.resource', dataset=dataset,
                                    rid=resource.id))
        self.assert200(response)
        data = json.loads(response.data)
        assert data['title'] == resource.title
        assert data['latest'] == resource.latest
        assert data['url'] == resource.url

    def test_create(self):
        data = ResourceFactory.as_dict()
        data['extras'] = {'extra:id': 'id'}
        data['filetype'] = 'remote'
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)
        self.assertEqual(self.dataset.resources[0].extras, {'extra:id': 'id'})

    def test_unallowed_create_filetype_file(self):
        data = ResourceFactory.as_dict()
        data['filetype'] = 'file'  # to be explicit
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        # should fail because the POST endpoint only supports URL setting for remote resources
        self.assert400(response)

    def test_create_normalize_format(self):
        _format = ' FORMAT '
        data = ResourceFactory.as_dict()
        data['filetype'] = 'remote'
        data['format'] = _format
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(self.dataset.resources[0].format,
                         _format.strip().lower())

    def test_create_2nd(self):
        self.dataset.resources.append(ResourceFactory())
        self.dataset.save()

        data = ResourceFactory.as_dict()
        data['filetype'] = 'remote'
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 2)

    def test_create_with_file(self):
        '''It should create a resource from the API with a file'''
        user = self.login()
        with self.autoindex():
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(organization=org)
        response = self.post(
            url_for('api.upload_new_dataset_resource', dataset=dataset),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert201(response)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')
        response = self.put(
            url_for('api.resource', dataset=dataset, rid=data['id']), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(len(dataset.resources), 1)
        self.assertTrue(dataset.resources[0].url.endswith('test.txt'))

    def test_create_with_file_chunks(self):
        '''It should create a resource from the API with a chunked file'''
        user = self.login()
        with self.autoindex():
            org = OrganizationFactory(members=[
                Member(user=user, role='admin')
            ])
            dataset = DatasetFactory(organization=org)

        uuid = str(uuid4())
        parts = 4
        url = url_for('api.upload_new_dataset_resource', dataset=dataset)

        for i in range(parts):
            response = self.post(url, {
                'file': (BytesIO(b'a'), 'blob'),
                'uuid': uuid,
                'filename': 'test.txt',
                'partindex': i,
                'partbyteoffset': 0,
                'totalfilesize': parts,
                'totalparts': parts,
                'chunksize': 1,
            }, json=False)

            self.assert200(response)
            assert response.json['success']
            assert 'filename' not in response.json
            assert 'url' not in response.json
            assert 'size' not in response.json
            assert 'sha1' not in response.json
            assert 'url' not in response.json

        response = self.post(url, {
            'uuid': uuid,
            'filename': 'test.txt',
            'totalfilesize': parts,
            'totalparts': parts,
        }, json=False)
        self.assert201(response)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')

    def test_reorder(self):
        # Register an extra field in order to test
        # https://github.com/opendatateam/udata/issues/1794
        ResourceMixin.extras.register('my:register', db.BooleanField)
        self.dataset.resources = ResourceFactory.build_batch(3)
        self.dataset.resources[0].extras = {
            'my:register': True,
        }
        self.dataset.save()
        self.dataset.reload()  # Otherwise `last_modified` date is inaccurate.
        initial_last_modified = self.dataset.last_modified

        initial_order = [r.id for r in self.dataset.resources]
        expected_order = [{'id': str(id)} for id in reversed(initial_order)]

        with self.api_user():
            response = self.put(url_for('api.resources', dataset=self.dataset),
                                expected_order)
        self.assertStatus(response, 200)
        self.assertEqual([str(r['id']) for r in response.json],
                         [str(r['id']) for r in expected_order])
        self.dataset.reload()
        self.assertEqual([str(r.id) for r in self.dataset.resources],
                         [str(r['id']) for r in expected_order])
        self.assertEqual(self.dataset.last_modified, initial_last_modified)

    def test_update_local(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        now = datetime.now()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'published': now.isoformat(),
            'extras': {
                'extra:id': 'id',
            }
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
        # Url should NOT have been updated as it is a hosted resource
        self.assertNotEqual(updated.url, data['url'])
        self.assertEqual(updated.extras, {'extra:id': 'id'})
        self.assertEqualDates(updated.published, now)

    def test_update_remote(self):
        resource = ResourceFactory()
        resource.filetype = 'remote'
        self.dataset.resources.append(resource)
        self.dataset.save()
        now = datetime.now()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'published': now.isoformat(),
            'extras': {
                'extra:id': 'id',
            }
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
        # Url should have been updated as it is a remote resource
        self.assertEqual(updated.url, data['url'])
        self.assertEqual(updated.extras, {'extra:id': 'id'})
        self.assertEqualDates(updated.published, now)

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
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'test.txt')
        response = self.put(
            url_for('api.resource', dataset=dataset, rid=data['id']), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(len(dataset.resources), 1)
        self.assertTrue(dataset.resources[0].url.endswith('test.txt'))

    def test_file_update_old_file_deletion(self):
        '''It should update a resource's file and delete the old one'''
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        with self.api_user():
            upload_response = self.post(
                url_for(
                    'api.upload_dataset_resource',
                    dataset=self.dataset,
                    rid=str(resource.id)
                    ), {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)

            data = json.loads(upload_response.data)
            self.assertEqual(data['title'], 'test.txt')

            upload_response = self.post(
                url_for(
                    'api.upload_dataset_resource',
                    dataset=self.dataset,
                    rid=str(resource.id)
                    ), {'file': (BytesIO(b'aaa'), 'test_update.txt')}, json=False)

            data = json.loads(upload_response.data)
            self.assertEqual(data['title'], 'test-update.txt')

        resource_strorage = list(storages.resources.list_files())
        self.assertEqual(len(resource_strorage), 1)
        self.assertEqual(resource_strorage[0][-15:], 'test-update.txt')

    def test_delete(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        with self.api_user():
            upload_response = self.post(
                url_for(
                    'api.upload_dataset_resource',
                    dataset=self.dataset,
                    rid=str(resource.id)
                    ), {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)

            data = json.loads(upload_response.data)
            self.assertEqual(data['title'], 'test.txt')

            response = self.delete(url_for('api.resource',
                                           dataset=self.dataset,
                                           rid=str(resource.id)))

        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 0)
        self.assertEqual(list(storages.resources.list_files()), [])

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
        self.assert201(response)

        to_follow.count_followers()
        self.assertEqual(to_follow.get_metrics()['followers'], 1)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        follow = Follow.objects.followers(to_follow).first()
        self.assertIsInstance(follow.following, Dataset)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_dataset(self):
        '''It should unfollow the dataset on DELETE'''
        user = self.login()
        to_follow = DatasetFactory()
        Follow.objects.create(follower=user, following=to_follow)

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

    def test_suggest_mime_api(self):
        '''It should suggest mime types'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(mime=f) for f in (
                    faker.mime_type(category=None),
                    faker.mime_type(category=None),
                    'application/test',
                    'application/test-1'
                )
            ])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        # Shortest match first.
        self.assertEqual(response.json[0]['text'], 'application/test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('application/test'))

    def test_suggest_mime_api_plus(self):
        '''It should suggest mime types'''
        with self.autoindex():
            DatasetFactory(resources=[ResourceFactory(mime='application/test+suffix')])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'suff', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['text'], 'application/test+suffix')

    def test_suggest_mime_api_no_match(self):
        '''It should not provide format suggestion if no match'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(mime=faker.word()) for _ in range(3)
            ])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_mime_api_empty(self):
        '''It should not provide mime suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api(self):
        '''It should suggest datasets'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    title='test-{0}'.format(i) if i % 2 else faker.word(),
                    visible=True)

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

    def test_suggest_datasets_acronym_api(self):
        '''It should suggest datasets from their acronyms'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    # Ensure title does not contains 'tes'
                    title=faker.unique_string(),
                    acronym='test-{0}'.format(i) if i % 2 else None,
                    visible=True)

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
            self.assertNotIn('tes', suggestion['title'])
            self.assertTrue(suggestion['acronym'].startswith('test'))

    def test_suggest_datasets_api_unicode(self):
        '''It should suggest datasets with special characters'''
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

    def test_dataset_allowed_resources_extensions(self):
        '''It should fetch the resources allowed extensions list from the API'''
        extensions = ['csv', 'json', 'xml']
        self.app.config['ALLOWED_RESOURCES_EXTENSIONS'] = extensions
        response = self.get(url_for('api.allowed_extensions'))
        self.assert200(response)
        self.assertEqual(response.json, extensions)


class DatasetArchivedAPITest(APITestCase):
    modules = ['core.dataset']

    def test_dataset_api_search_archived(self):
        '''It should search datasets from the API, excluding archived ones'''
        with self.autoindex():
            VisibleDatasetFactory(archived=None)
            dataset = VisibleDatasetFactory(archived=datetime.now())

        response = self.get(url_for('api.datasets', q=''))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertNotIn(str(dataset.id),
                         [r['id'] for r in response.json['data']])

    def test_dataset_api_get_archived(self):
        '''It should fetch an archived dataset from the API and return 200'''
        dataset = VisibleDatasetFactory(archived=datetime.now())
        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)


class CommunityResourceAPITest(APITestCase):
    modules = ['core.dataset', 'core.user', 'core.organization']

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

    def test_community_resource_api_create_dataset_binding(self):
        '''It should create a community resource linked to the right dataset'''
        dataset = VisibleDatasetFactory()
        self.login()
        response = self.post(
            url_for('api.upload_new_community_resource', dataset=dataset),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert201(response)
        self.assertEqual(CommunityResource.objects.count(), 1)
        community_resource = CommunityResource.objects.first()
        self.assertEqual(community_resource.dataset, dataset)

    def test_community_resource_api_create(self):
        '''It should create a community resource from the API'''
        dataset = VisibleDatasetFactory()
        self.login()
        response = self.post(
            url_for('api.upload_new_community_resource', dataset=dataset),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert201(response)
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

    def test_community_resource_api_create_as_org(self):
        '''It should create a community resource as org from the API'''
        dataset = VisibleDatasetFactory()
        user = self.login()
        org = OrganizationFactory(members=[
            Member(user=user, role='admin')
        ])
        response = self.post(
            url_for('api.upload_new_community_resource', dataset=dataset),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert201(response)
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

    def test_community_resource_api_update(self):
        '''It should update a community resource from the API'''
        user = self.login()
        community_resource = CommunityResourceFactory(owner=user)
        data = community_resource.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.community_resource',
                                    community=community_resource),
                            data)
        self.assert200(response)
        self.assertEqual(CommunityResource.objects.count(), 1)
        self.assertEqual(CommunityResource.objects.first().description,
                         'new description')

    def test_community_resource_api_update_w_previous_owner(self):
        '''Should update a community resource and keep the original author'''
        owner = UserFactory()
        community_resource = CommunityResourceFactory(owner=owner)
        self.login(AdminFactory())
        data = community_resource.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.community_resource',
                                    community=community_resource),
                            data)
        self.assert200(response)
        self.assertEqual(CommunityResource.objects.first().owner,
                         owner)

    def test_community_resource_api_update_with_file(self):
        '''It should update a community resource file from the API'''
        dataset = VisibleDatasetFactory()
        user = self.login()
        community_resource = CommunityResourceFactory(dataset=dataset,
                                                      owner=user)
        response = self.post(
            url_for('api.upload_community_resource',
                    community=community_resource),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
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
    
    def test_community_resource_file_update_old_file_deletion(self):
        '''It should update a community resource's file and delete the old one'''
        dataset = VisibleDatasetFactory()
        user = self.login()
        community_resource = CommunityResourceFactory(dataset=dataset,
                                                      owner=user)
        response = self.post(
            url_for('api.upload_community_resource',
                    community=community_resource),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))
        self.assertEqual(data['title'], 'test.txt')

        response = self.post(
            url_for('api.upload_community_resource',
                    community=community_resource),
            {'file': (BytesIO(b'aaa'), 'test_update.txt')}, json=False)
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))
        self.assertEqual(data['title'], 'test-update.txt')

        self.assertEqual(len(list(storages.resources.list_files())), 1)

    def test_community_resource_api_create_remote(self):
        '''It should create a remote community resource from the API'''
        user = self.login()
        dataset = VisibleDatasetFactory()
        attrs = CommunityResourceFactory.as_dict()
        attrs['filetype'] = 'remote'
        attrs['dataset'] = str(dataset.id)
        response = self.post(
            url_for('api.community_resources'),
            attrs
        )
        self.assert201(response)
        data = json.loads(response.data)
        self.assertEqual(data['title'], attrs['title'])
        self.assertEqual(data['url'], attrs['url'])
        self.assertEqual(CommunityResource.objects.count(), 1)
        community_resource = CommunityResource.objects.first()
        self.assertEqual(community_resource.dataset, dataset)
        self.assertEqual(community_resource.owner, user)
        self.assertIsNone(community_resource.organization)

    def test_community_resource_api_unallowed_create_filetype_file(self):
        '''It should create a remote community resource from the API'''
        user = self.login()
        dataset = VisibleDatasetFactory()
        attrs = CommunityResourceFactory.as_dict()
        attrs['filetype'] = 'file'  # to be explicit
        attrs['dataset'] = str(dataset.id)
        response = self.post(
            url_for('api.community_resources'),
            attrs
        )
        # should fail because the POST endpoint only supports URL setting for remote community resources
        self.assert400(response)

    def test_community_resource_api_create_remote_needs_dataset(self):
        '''
        It should prevent remote community resource creation without dataset
        from the API
        '''
        self.login()
        attrs = CommunityResourceFactory.as_dict()
        attrs['filetype'] = 'remote'
        response = self.post(
            url_for('api.community_resources'),
            attrs
        )
        self.assertStatus(response, 400)
        data = json.loads(response.data)
        self.assertIn('errors', data)
        self.assertIn('dataset', data['errors'])
        self.assertEqual(CommunityResource.objects.count(), 0)

    def test_community_resource_api_create_remote_needs_real_dataset(self):
        '''
        It should prevent remote community resource creation without a valid
        dataset identifier
        '''
        self.login()
        attrs = CommunityResourceFactory.as_dict()
        attrs['dataset'] = 'xxx'
        response = self.post(
            url_for('api.community_resources'),
            attrs
        )
        self.assertStatus(response, 400)
        data = json.loads(response.data)
        self.assertIn('errors', data)
        self.assertIn('dataset', data['errors'])
        self.assertEqual(CommunityResource.objects.count(), 0)

    def test_community_resource_api_delete(self):
        dataset = VisibleDatasetFactory()
        self.login()

        response = self.post(
            url_for('api.upload_new_community_resource', dataset=dataset),
            {'file': (BytesIO(b'aaa'), 'test.txt')}, json=False)
        self.assert201(response)

        data = json.loads(response.data)
        resource_id = data['id']
        self.assertEqual(data['title'], 'test.txt')

        response = self.put(
            url_for('api.community_resource', community=resource_id),
            data)
        self.assertStatus(response, 200)
        self.assertEqual(CommunityResource.objects.count(), 1)

        response = self.delete(url_for('api.community_resource', community=resource_id))
        self.assertStatus(response, 204)

        self.assertEqual(CommunityResource.objects.count(), 0)
        self.assertEqual(list(storages.resources.list_files()), [])

class ResourcesTypesAPITest(APITestCase):

    def test_resource_types_list(self):
        '''It should fetch the resource types list from the API'''
        response = self.get(url_for('api.resource_types'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(RESOURCE_TYPES))


@pytest.mark.usefixtures('clean_db')
class DatasetSchemasAPITest:
    modules = ['core.dataset']

    def test_dataset_schemas_api_list(self, api, rmock, app):
        # Can't use @pytest.mark.options otherwise a request will be
        # made before setting up rmock at module load, resulting in a 404
        app.config['SCHEMA_CATALOG_URL'] = 'https://example.com/schemas'

        rmock.get('https://example.com/schemas', json={
            'schemas': [{"name": "etalab/schema-irve", "title": "Schéma IRVE"}]
        })

        response = api.get(url_for('api.schemas'))

        assert200(response)
        assert response.json == [{"id": "etalab/schema-irve", "label": "Schéma IRVE"}]

    @pytest.mark.options(SCHEMA_CATALOG_URL=None)
    def test_dataset_schemas_api_list_no_catalog_url(self, api):
        response = api.get(url_for('api.schemas'))

        assert200(response)
        assert response.json == []

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/notfound')
    def test_dataset_schemas_api_list_not_found(self, api):
        response = api.get(url_for('api.schemas'))
        assert404(response)

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    def test_dataset_schemas_api_list_error_no_cache(self, api, rmock):
        rmock.get('https://example.com/schemas', status_code=500)

        response = api.get(url_for('api.schemas'))
        assert response.status_code == 503

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    def test_dataset_schemas_api_list_error_w_cache(self, api, rmock, mocker):
        cache_mock_set = mocker.patch.object(cache, 'set')
        mocker.patch.object(cache, 'get', return_value=[{"id": "etalab/schema-irve", "label": "Schéma IRVE"}])

        # Fill cache
        rmock.get('https://example.com/schemas', json={
            'schemas': [{"name": "etalab/schema-irve", "title": "Schéma IRVE"}]
        })
        response = api.get(url_for('api.schemas'))
        assert200(response)
        assert response.json == [{"id": "etalab/schema-irve", "label": "Schéma IRVE"}]
        assert cache_mock_set.called

        # Endpoint becomes unavailable
        rmock.get('https://example.com/schemas', status_code=500)

        # Long term cache is used
        response = api.get(url_for('api.schemas'))
        assert200(response)
        assert response.json == [{"id": "etalab/schema-irve", "label": "Schéma IRVE"}]

