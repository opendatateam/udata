import json
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
import pytz
from flask import url_for
import requests_mock

from udata.api import fields
from udata.app import cache
from udata.core import storages
from udata.core.badges.factories import badge_factory
from udata.core.dataset.api_fields import (dataset_harvest_fields,
                                           resource_harvest_fields)
from udata.core.dataset.factories import (CommunityResourceFactory,
                                          DatasetFactory, LicenseFactory,
                                          ResourceFactory, ResourceSchemaMockData,
                                          VisibleDatasetFactory)
from udata.core.dataset.models import (HarvestDatasetMetadata,
                                       HarvestResourceMetadata, ResourceMixin)
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.core.topic.factories import TopicFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.i18n import gettext as _
from udata.models import (LEGACY_FREQUENCIES, RESOURCE_TYPES,
                          UPDATE_FREQUENCIES, CommunityResource, Dataset,
                          Follow, Member, db)
from udata.tags import MAX_TAG_LENGTH, MIN_TAG_LENGTH
from udata.tests.features.territories import create_geozones_fixtures
from udata.tests.helpers import assert200, assert404, assert204
from udata.utils import faker, unique_string

from . import APITestCase

SAMPLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],  # noqa
        [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]],  # noqa
         [[100.2, 0.2], [100.8, 0.2], [100.8, 0.8], [100.2, 0.8], [100.2, 0.2]]]
    ]
}

class DatasetAPITest(APITestCase):
    modules = []

    def test_dataset_api_list(self):
        '''It should fetch a dataset list from the API'''
        datasets = [VisibleDatasetFactory() for i in range(2)]

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))
        self.assertTrue('quality' in response.json['data'][0])

    def test_dataset_api_full_text_search(self):
        '''Should proceed to full text search on datasets'''
        [VisibleDatasetFactory() for i in range(2)]
        VisibleDatasetFactory(title="some spécial integer")
        VisibleDatasetFactory(title="some spécial float")
        dataset = VisibleDatasetFactory(title="some spécial chars")

        # with accent
        response = self.get(url_for('api.datasets', q='some spécial chars'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(dataset.id))

        # with accent
        response = self.get(url_for('api.datasets', q='spécial'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)

        # without accent
        response = self.get(url_for('api.datasets', q='special'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)

    def test_dataset_api_sorting(self):
        '''Should sort datasets results from the API'''
        self.login()
        [VisibleDatasetFactory() for i in range(2)]

        to_follow = VisibleDatasetFactory(title="dataset to follow")

        response = self.post(url_for('api.dataset_followers', id=to_follow.id))
        self.assert201(response)

        to_follow.count_followers()
        self.assertEqual(to_follow.get_metrics()['followers'], 1)

        # without accent
        response = self.get(url_for('api.datasets', sort='-followers'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(response.json['data'][0]['id'], str(to_follow.id))

    def test_dataset_api_sorting_created(self):
        self.login()
        first = VisibleDatasetFactory(title="first created dataset")
        second = VisibleDatasetFactory(title="second created dataset")
        response = self.get(url_for('api.datasets', sort='created'))
        self.assert200(response)
        self.assertEqual(response.json['data'][0]['id'], str(first.id))

        response = self.get(url_for('api.datasets', sort='-created'))
        self.assert200(response)
        self.assertEqual(response.json['data'][0]['id'], str(second.id))

        second.title = "second updated dataset"
        second.save()
        response = self.get(url_for('api.datasets', sort='-last_update'))
        self.assert200(response)
        self.assertEqual(response.json['data'][0]['id'], str(second.id))

        response = self.get(url_for('api.datasets', sort='last_update'))
        self.assert200(response)
        self.assertEqual(response.json['data'][0]['id'], str(first.id))

    def test_dataset_api_default_sorting(self):
        # Default sort should be -created
        self.login()
        [VisibleDatasetFactory(title="some created dataset") for i in range(10)]
        last = VisibleDatasetFactory(title="last created dataset")
        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(response.json['data'][0]['id'], str(last.id))

    def test_dataset_api_list_with_filters(self):
        '''Should filters datasets results based on query filters'''
        owner = UserFactory()
        org = OrganizationFactory()

        [VisibleDatasetFactory() for i in range(2)]

        tag_dataset = VisibleDatasetFactory(tags=['my-tag', 'other'])
        license_dataset = VisibleDatasetFactory(license=LicenseFactory(id='cc-by'))
        format_dataset = DatasetFactory(resources=[ResourceFactory(format='my-format')])
        featured_dataset = VisibleDatasetFactory(featured=True)
        topic_dataset = VisibleDatasetFactory()
        topic = TopicFactory(datasets=[topic_dataset])

        paca, _, _ = create_geozones_fixtures()
        geozone_dataset = VisibleDatasetFactory(spatial=SpatialCoverageFactory(zones=[paca.id]))
        granularity_dataset = VisibleDatasetFactory(
            spatial=SpatialCoverageFactory(granularity='country')
        )

        temporal_coverage = db.DateRange(start='2022-05-03', end='2022-05-04')
        temporal_coverage_dataset = DatasetFactory(temporal_coverage=temporal_coverage)

        owner_dataset = VisibleDatasetFactory(owner=owner)
        org_dataset = VisibleDatasetFactory(organization=org)

        schema_dataset = VisibleDatasetFactory(resources=[
            ResourceFactory(schema={'name': 'my-schema', 'url': 'https://example.org', 'version': '1.0.0'})
        ])
        schema_version2_dataset = VisibleDatasetFactory(resources=[
            ResourceFactory(schema={'name': 'other-schema', 'url': 'https://example.org', 'version': '2.0.0'})
        ])

        # filter on tag
        response = self.get(url_for('api.datasets', tag='my-tag'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(tag_dataset.id))

        # filter on format
        response = self.get(url_for('api.datasets', format='my-format'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(format_dataset.id))

        # filter on featured
        response = self.get(url_for('api.datasets', featured='true'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(featured_dataset.id))

        # filter on license
        response = self.get(url_for('api.datasets', license='cc-by'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(license_dataset.id))

        # filter on geozone
        response = self.get(url_for('api.datasets', geozone=paca.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(geozone_dataset.id))

        # filter on granularity
        response = self.get(url_for('api.datasets', granularity='country'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(granularity_dataset.id))

        # filter on temporal_coverage
        response = self.get(url_for('api.datasets', temporal_coverage='2022-05-03-2022-05-04'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(temporal_coverage_dataset.id))

        # filter on owner
        response = self.get(url_for('api.datasets', owner=owner.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(owner_dataset.id))

        response = self.get(url_for('api.datasets', owner='owner-id'))
        self.assert400(response)

        # filter on organization
        response = self.get(url_for('api.datasets', organization=org.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(org_dataset.id))

        response = self.get(url_for('api.datasets', organization='org-id'))
        self.assert400(response)

        # filter on schema
        response = self.get(url_for('api.datasets', schema='my-schema'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(schema_dataset.id))

        # filter on schema version
        response = self.get(url_for('api.datasets', schema_version='2.0.0'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(schema_version2_dataset.id))

        # filter on topic
        response = self.get(url_for('api.datasets', topic=topic.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(topic_dataset.id))

        # filter on non existing topic
        response = self.get(url_for('api.datasets', topic=topic_dataset.id))
        self.assert200(response)
        self.assertTrue(len(response.json['data']) > 0)

        # filter on non id for topic
        response = self.get(url_for('api.datasets', topic='xxx'))
        self.assert400(response)

    def test_dataset_api_get(self):
        '''It should fetch a dataset from the API'''
        resources = [ResourceFactory() for _ in range(2)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(len(data['resources']), len(resources))
        self.assertTrue('quality' in data)
        self.assertTrue('internal' in data)
        # Reloads dataset from mongoDB to get mongoDB's date's milliseconds reset.
        dataset.reload()
        self.assertEqual(data['internal']['created_at_internal'], fields.ISODateTime().format(dataset.created_at_internal))
        self.assertEqual(data['internal']['last_modified_internal'], fields.ISODateTime().format(dataset.last_modified_internal))

        self.assertTrue('internal' in data['resources'][0])
        self.assertEqual(data['resources'][0]['internal']['created_at_internal'], fields.ISODateTime().format(dataset.resources[0].created_at_internal))
        self.assertEqual(data['resources'][0]['internal']['last_modified_internal'], fields.ISODateTime().format(dataset.resources[0].last_modified_internal))

    def test_dataset_api_get_deleted(self):
        '''It should not fetch a deleted dataset from the API and raise 410'''
        dataset = VisibleDatasetFactory(deleted=datetime.utcnow())

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert410(response)

    def test_dataset_api_get_deleted_but_authorized(self):
        '''It should a deleted dataset from the API if user is authorized'''
        self.login()
        dataset = VisibleDatasetFactory(owner=self.user,
                                        deleted=datetime.utcnow())

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
            'dict': {
                'foo': 'bar',
            }
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')
        self.assertEqual(dataset.extras['dict']['foo'], 'bar')

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

    def test_dataset_api_update_private(self):
        user = self.login()
        dataset = DatasetFactory(owner=user, private=True)
        data = dataset.to_dict()
        data['description'] = 'new description'
        del data['private']

        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(dataset.description, 'new description')
        self.assertEqual(dataset.private, True)
        
        data['private'] = None
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(dataset.private, False)

        data['private'] = True
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        self.assertEqual(dataset.private, True)



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
        dataset = DatasetFactory(owner=user, deleted=datetime.utcnow())
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert410(response)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         dataset.description)

    def test_dataset_api_update_contact_point(self):
        '''It should update a dataset from the API'''
        self.login()

        # Org and contact point creation
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        contact_point_data = {
            'email': 'mooneywayne@cobb-cochran.com',
            'name': 'Martin Schultz',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.contact_points'), contact_point_data)
        self.assert201(response)

        response = self.get(url_for('api.org_contact_points', org=org))
        assert200(response)
        contact_point_id = response.json['data'][0]['id']

        # Dataset creation
        dataset = DatasetFactory(organization=org)
        data = DatasetFactory.as_dict()

        data['contact_point'] = contact_point_id
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.contact_point.name, contact_point_data['name'])

        data['contact_point'] = None
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.contact_point, None)

    def test_dataset_api_update_contact_point_error(self):
        '''It should update a dataset from the API'''
        self.login()

        # Org and contact point creation
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        contact_point_data = {
            'email': 'mooneywayne@cobb-cochran.com',
            'name': 'Martin Schultz',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.contact_points'), contact_point_data)
        self.assert201(response)

        response = self.get(url_for('api.org_contact_points', org=org))
        assert200(response)
        contact_point_id = response.json['data'][0]['id']

        # Dataset creation
        dataset = DatasetFactory(owner=self.user)
        data = DatasetFactory.as_dict()

        data['contact_point'] = contact_point_id
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert400(response)
        self.assertEqual(response.json['errors']['contact_point'][0], _('Wrong contact point id or contact point ownership mismatch'))

    def test_dataset_api_delete(self):
        '''It should delete a dataset from the API'''
        user = self.login()
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
        dataset = VisibleDatasetFactory(owner=user, deleted=datetime.utcnow())
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

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    @requests_mock.Mocker(kw='rmock')
    def test_dataset_new_resource_with_schema(self, rmock):
        '''Tests api validation to prevent schema creation with a name and a url'''
        rmock.get('https://example.com/schemas', json=ResourceSchemaMockData.get_mock_data())

        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        resource_data = ResourceFactory.as_dict()

        resource_data['schema'] = {'url': 'test'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert400(response)
        assert response.json['errors']['resources'][0]['schema']['url'] == [_('Invalid URL')]

        resource_data['schema'] = {'name': 'unknown-schema'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert400(response)
        assert response.json['errors']['resources'][0]['schema']['name'] == [_('Schema name "{schema}" is not an allowed value. Allowed values: {values}').format(schema='unknown-schema', values='etalab/schema-irve-statique, 139bercy/format-commande-publique')]

        resource_data['schema'] = {'name': 'etalab/schema-irve-statique', 'version': '42.0.0'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert400(response)
        assert response.json['errors']['resources'][0]['schema']['version'] == [_('Version "{version}" is not an allowed value for the schema "{name}". Allowed versions: {values}').format(version='42.0.0', name='etalab/schema-irve-statique', values='2.2.0, 2.2.1, latest')]

        resource_data['schema'] = {'url': 'http://example.com', 'name': 'etalab/schema-irve-statique'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        assert dataset.resources[0].schema['url'] == 'http://example.com'
        assert dataset.resources[0].schema['name'] == 'etalab/schema-irve-statique'
        assert dataset.resources[0].schema['version'] == None

        resource_data['schema'] = {'name': 'etalab/schema-irve-statique'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        assert dataset.resources[0].schema['name'] == 'etalab/schema-irve-statique'
        assert dataset.resources[0].schema['url'] == None
        assert dataset.resources[0].schema['version'] == None

        resource_data['schema'] = {'name': 'etalab/schema-irve-statique', 'version': '2.2.0'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        assert dataset.resources[0].schema['name'] == 'etalab/schema-irve-statique'
        assert dataset.resources[0].schema['url'] == None
        assert dataset.resources[0].schema['version'] == '2.2.0'

        resource_data['schema'] = {'url': 'https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/2.2.1/schema-statique.json'}
        data['resources'].append(resource_data)
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        assert dataset.resources[0].schema['name'] == 'etalab/schema-irve-statique'
        assert dataset.resources[0].schema['url'] == None
        assert dataset.resources[0].schema['version'] == '2.2.1'

        # Putting `None` as the schema argument do not remove the schema
        # Not sure if it's the correct behaviour but it's the normal behaviour on the API v1… :-(
        # I think it should be if the key 'schema' is missing, the old value is kept, if the key is present
        # but `None` update it inside the DB as `None`.
        data = response.json
        data['resources'][0]['schema'] = None
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        assert dataset.resources[0].schema['name'] == 'etalab/schema-irve-statique'
        assert dataset.resources[0].schema['url'] == None
        assert dataset.resources[0].schema['version'] == '2.2.1'

        # Putting `None` as the schema name and version remove the schema
        # This is a workaround for the None on schema behaviour explain above.
        data = response.json
        data['resources'][0]['schema']['name'] = None
        data['resources'][0]['schema']['version'] = None

        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)

        dataset.reload()
        assert dataset.resources[0].schema['name'] == None
        assert dataset.resources[0].schema['url'] == None
        assert dataset.resources[0].schema['version'] == None


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
        response = self.post(
            url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_same(self):
        data = self.factory.as_dict()
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
        response = self.post(
            url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 2)

    def test_delete(self):
        badge = self.factory()
        self.dataset.add_badge(badge.kind)
        response = self.delete(
            url_for('api.dataset_badge', dataset=self.dataset,
                    badge_kind=str(badge.kind)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 0)

    def test_delete_404(self):
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
        response = self.post(url_for('api.resources',
                                     dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)
        self.assertEqual(self.dataset.resources[0].extras, {'extra:id': 'id'})

    def test_unallowed_create_filetype_file(self):
        data = ResourceFactory.as_dict()
        data['filetype'] = 'file'  # to be explicit
        response = self.post(url_for('api.resources',
                                     dataset=self.dataset), data)
        # should fail because the POST endpoint only supports URL setting for remote resources
        self.assert400(response)

    def test_create_normalize_format(self):
        _format = ' FORMAT '
        data = ResourceFactory.as_dict()
        data['filetype'] = 'remote'
        data['format'] = _format
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
        response = self.post(url_for('api.resources',
                                     dataset=self.dataset), data)
        self.assert201(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 2)

    def test_create_with_file(self):
        '''It should create a resource from the API with a file'''
        user = self.login()
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
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'extras': {
                'extra:id': 'id',
            }
        }
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

    def test_update_remote(self):
        resource = ResourceFactory()
        resource.filetype = 'remote'
        self.dataset.resources.append(resource)
        self.dataset.save()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'extras': {
                'extra:id': 'id',
            }
        }
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

    def test_bulk_update(self):
        resources = ResourceFactory.build_batch(2)
        self.dataset.resources.extend(resources)
        self.dataset.save()
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
        response = self.put(url_for('api.resources', dataset=self.dataset), data)
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

    def test_update_404(self):
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        }
        response = self.put(url_for('api.resource',
                                    dataset=self.dataset,
                                    rid=str(ResourceFactory().id)), data)
        self.assert404(response)

    def test_update_with_file(self):
        '''It should update a resource from the API with a file'''
        user = self.login()
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
        DatasetFactory(resources=[
            ResourceFactory(format=f)
            for f in (faker.word(), faker.word(), 'kml', 'kml-1')
        ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'km', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('km', suggestion['text'])

    def test_suggest_format_api_no_match(self):
        '''It should not provide format suggestion if no match'''
        DatasetFactory(resources=[
            ResourceFactory(format=faker.word()) for _ in range(3)
        ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_format_api_empty(self):
        '''It should not provide format suggestion if no data'''
        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_mime_api(self):
        '''It should suggest mime types'''
        DatasetFactory(resources=[
            ResourceFactory(mime=f) for f in (
                faker.mime_type(category=None),
                faker.mime_type(category=None),
                'application/json',
                'application/json-1'
            )
        ])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'js', 'size': '5'})
        self.assert200(response)
        self.assertLessEqual(len(response.json), 5)

        for suggestion in response.json:
            self.assertIn('text', suggestion)

    def test_suggest_mime_api_plus(self):
        '''It should suggest mime types'''
        DatasetFactory(resources=[ResourceFactory(mime='application/xhtml+xml')])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'xml', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 5)

    def test_suggest_mime_api_no_match(self):
        '''It should not provide format suggestion if no match'''
        DatasetFactory(resources=[
            ResourceFactory(mime=faker.word()) for _ in range(3)
        ])

        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_mime_api_empty(self):
        '''It should not provide mime suggestion if no data'''
        response = self.get(url_for('api.suggest_mime'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api(self):
        '''It should suggest datasets'''
        for i in range(3):
            DatasetFactory(
                title='title-test-{0}'.format(i) if i % 2 else faker.word(),
                visible=True,
                metrics={"followers": i})
        max_follower_dataset = DatasetFactory(
            title='title-test-4',
            visible=True,
            metrics={"followers": 10}
        )

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'title-test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertIn('title-test', suggestion['title'])
        self.assertEqual(response.json[0]['id'], str(max_follower_dataset.id))

    def test_suggest_datasets_acronym_api(self):
        '''It should suggest datasets from their acronyms'''
        for i in range(4):
            DatasetFactory(
                # Ensure title does not contains 'acronym-tes'
                title=faker.unique_string(),
                acronym='acronym-test-{0}'.format(i) if i % 2 else None,
                visible=True)

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'acronym-test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertNotIn('tes', suggestion['title'])
            self.assertIn('acronym-test', suggestion['acronym'])

    def test_suggest_datasets_api_unicode(self):
        '''It should suggest datasets with special characters'''
        for i in range(4):
            DatasetFactory(
                title='title-testé-{0}'.format(i) if i % 2 else faker.word(),
                resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'title-testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertIn('title-testé', suggestion['title'])

    def test_suggest_datasets_api_no_match(self):
        '''It should not provide dataset suggestion if no match'''
        for i in range(3):
            DatasetFactory(resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api_empty(self):
        '''It should not provide dataset suggestion if no data'''
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
    modules = []

    def test_dataset_api_search_archived(self):
        '''It should search datasets from the API, excluding archived ones'''
        VisibleDatasetFactory(archived=None)
        dataset = VisibleDatasetFactory(archived=datetime.utcnow())

        response = self.get(url_for('api.datasets', q=''))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertNotIn(str(dataset.id),
                         [r['id'] for r in response.json['data']])

    def test_dataset_api_get_archived(self):
        '''It should fetch an archived dataset from the API and return 200'''
        dataset = VisibleDatasetFactory(archived=datetime.utcnow())
        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)


class CommunityResourceAPITest(APITestCase):
    modules = []

    def test_community_resource_api_get(self):
        '''It should fetch a community resource from the API'''
        community_resource = CommunityResourceFactory()

        response = self.get(url_for('api.community_resource',
                                    community=community_resource))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['id'], str(community_resource.id))

    def test_resources_api_list(self):
        '''It should list community resources from the API'''
        community_resources = [CommunityResourceFactory() for _ in range(40)]
        response = self.get(url_for('api.community_resources'))
        self.assert200(response)
        resources = json.loads(response.data)['data']

        response = self.get(url_for('api.community_resources', page=2))
        self.assert200(response)
        resources += json.loads(response.data)['data']

        self.assertEqual(len(resources), len(community_resources))
        # Assert we don't have duplicates
        self.assertEqual(len(set(res['id'] for res in resources)), len(community_resources))

    def test_community_resource_api_get_from_string_id(self):
        '''It should fetch a community resource from the API'''
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
        self.login()
        dataset = VisibleDatasetFactory()
        attrs = CommunityResourceFactory.as_dict()
        attrs['filetype'] = 'file'  # to be explicit
        attrs['dataset'] = str(dataset.id)
        response = self.post(
            url_for('api.community_resources'),
            attrs
        )
        # should fail because the POST endpoint only supports URL setting
        # for remote community resources
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
    modules = []

    def test_dataset_schemas_api_list(self, api, rmock, app):
        # Can't use @pytest.mark.options otherwise a request will be
        # made before setting up rmock at module load, resulting in a 404
        app.config['SCHEMA_CATALOG_URL'] = 'https://example.com/schemas'

        rmock.get('https://example.com/schemas', json=ResourceSchemaMockData.get_mock_data())
        response = api.get(url_for('api.schemas'))

        assert200(response)
        assert response.json == ResourceSchemaMockData.get_expected_v1_result_from_mock_data()

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
        mocker.patch.object(cache, 'get', return_value=ResourceSchemaMockData.get_mock_data()['schemas'])

        # Fill cache
        rmock.get('https://example.com/schemas', json=ResourceSchemaMockData.get_mock_data())
        response = api.get(url_for('api.schemas'))
        assert200(response)
        assert response.json == ResourceSchemaMockData.get_expected_v1_result_from_mock_data()
        assert cache_mock_set.called

        # Endpoint becomes unavailable
        rmock.get('https://example.com/schemas', status_code=500)

        # Long term cache is used
        response = api.get(url_for('api.schemas'))
        assert200(response)
        assert response.json == ResourceSchemaMockData.get_expected_v1_result_from_mock_data()


@pytest.mark.usefixtures('clean_db')
class HarvestMetadataAPITest:

    modules = []

    # api fields should be updated before app is created
    dataset_harvest_fields['dynamic_field'] = fields.String(description='', allow_null=True)
    resource_harvest_fields['dynamic_field'] = fields.String(description='', allow_null=True)

    def test_dataset_with_harvest_metadata(self, api):
        date = datetime(2022, 2, 22, tzinfo=pytz.UTC)
        harvest_metadata = HarvestDatasetMetadata(
            backend='DCAT',
            created_at=date,
            modified_at=date,
            source_id='source_id',
            remote_id='remote_id',
            domain='domain.gouv.fr',
            last_update=date,
            remote_url='http://domain.gouv.fr/dataset/remote_url',
            uri='http://domain.gouv.fr/dataset/uri',
            dct_identifier='http://domain.gouv.fr/dataset/identifier',
            archived_at=date,
            archived='not-on-remote'
        )
        dataset = DatasetFactory(harvest=harvest_metadata)

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['harvest'] == {
            'backend': 'DCAT',
            'created_at': date.isoformat(),
            'modified_at': date.isoformat(),
            'source_id': 'source_id',
            'remote_id': 'remote_id',
            'domain': 'domain.gouv.fr',
            'last_update': date.isoformat(),
            'remote_url': 'http://domain.gouv.fr/dataset/remote_url',
            'uri': 'http://domain.gouv.fr/dataset/uri',
            'dct_identifier': 'http://domain.gouv.fr/dataset/identifier',
            'archived_at': date.isoformat(),
            'archived': 'not-on-remote'
        }

    def test_dataset_dynamic_harvest_metadata_without_api_field(self, api):
        harvest_metadata = HarvestDatasetMetadata(
            dynamic_field_but_no_api_field_defined='DCAT'
        )
        dataset = DatasetFactory(harvest=harvest_metadata)

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['harvest'] == {}

    def test_dataset_dynamic_harvest_metadata_with_api_field(self, api):
        harvest_metadata = HarvestDatasetMetadata(
            dynamic_field='dynamic_value'
        )
        dataset = DatasetFactory(harvest=harvest_metadata)

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['harvest'] == {
            'dynamic_field': 'dynamic_value',
        }

    def test_dataset_with_resource_harvest_metadata(self, api):
        date = datetime(2022, 2, 22, tzinfo=pytz.UTC)

        harvest_metadata = HarvestResourceMetadata(
            created_at=date,
            modified_at=date,
            uri='http://domain.gouv.fr/dataset/uri',
        )
        dataset = DatasetFactory(resources=[ResourceFactory(harvest=harvest_metadata)])

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['resources'][0]['harvest'] == {
            'created_at': date.isoformat(),
            'modified_at': date.isoformat(),
            'uri': 'http://domain.gouv.fr/dataset/uri',
        }

    def test_resource_dynamic_harvest_metadata_without_api_field(self, api):
        harvest_metadata = HarvestResourceMetadata(
            dynamic_field_but_no_api_field_defined='dynamic_value'
        )
        dataset = DatasetFactory(resources=[ResourceFactory(harvest=harvest_metadata)])

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['resources'][0]['harvest'] == {}

    def test_resource_dynamic_harvest_metadata_with_api_field(self, api):
        harvest_metadata = HarvestResourceMetadata(
            dynamic_field='dynamic_value'
        )
        dataset = DatasetFactory(resources=[ResourceFactory(harvest=harvest_metadata)])

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['resources'][0]['harvest'] == {
            'dynamic_field': 'dynamic_value',
        }

    def test_dataset_with_harvest_computed_dates(self, api):
        creation_date = datetime(2022, 2, 22, tzinfo=pytz.UTC)
        modification_date = datetime(2022, 3, 19, tzinfo=pytz.UTC)
        harvest_metadata = HarvestDatasetMetadata(
            created_at=creation_date,
            modified_at=modification_date,
        )
        dataset = DatasetFactory(harvest=harvest_metadata)

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['created_at'] == creation_date.isoformat()
        assert response.json['last_modified'] == modification_date.isoformat()

        resource_harvest_metadata = HarvestResourceMetadata(
            created_at=creation_date,
            modified_at=modification_date,
        )
        dataset = DatasetFactory(resources=[ResourceFactory(harvest=resource_harvest_metadata)])

        response = api.get(url_for('api.dataset', dataset=dataset))
        assert200(response)
        assert response.json['resources'][0]['created_at'] == creation_date.isoformat()
        assert response.json['resources'][0]['last_modified'] == modification_date.isoformat()
