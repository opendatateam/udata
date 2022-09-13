from flask import url_for

from udata.tests.api import APITestCase

from udata.core.dataset.apiv2_schemas import DEFAULT_PAGE_SIZE
from udata.core.dataset.factories import (
    VisibleDatasetFactory, DatasetFactory, ResourceFactory, CommunityResourceFactory, LicenseFactory)
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.tests.features.territories import create_geozones_fixtures
from udata.models import (
    CommunityResource, Dataset, Follow, Member, UPDATE_FREQUENCIES,
    LEGACY_FREQUENCIES, RESOURCE_TYPES, db
)
from udata.tags import MIN_TAG_LENGTH, MAX_TAG_LENGTH
from udata.utils import unique_string

SAMPLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],  # noqa
        [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]],  # noqa
        [[100.2, 0.2], [100.8, 0.2], [100.8, 0.8], [100.2, 0.8], [100.2, 0.2]]]
    ]
}


class DatasetAPIV2Test(APITestCase):

    def test_get_dataset_list(self):
        '''It should fetch a dataset list from the API'''
        datasets = [VisibleDatasetFactory() for i in range(2)]

        response = self.get(url_for('apiv2.list_datasets'))
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
        response = self.get(url_for('apiv2.list_datasets', q='some spécial chars'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(dataset.id))

        # with accent
        response = self.get(url_for('apiv2.list_datasets', q='spécial'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)

        # without accent
        response = self.get(url_for('apiv2.list_datasets', q='special'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)

    def test_dataset_api_sorting(self):
        '''Should sort datasets results from the API'''
        user = self.login()
        [VisibleDatasetFactory() for i in range(2)]

        to_follow = VisibleDatasetFactory(title="dataset to follow")

        response = self.post(url_for('api.dataset_followers', id=to_follow.id))
        self.assert201(response)

        to_follow.count_followers()
        self.assertEqual(to_follow.get_metrics()['followers'], 1)

        # without accent
        response = self.get(url_for('apiv2.list_datasets', sort='-followers'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(response.json['data'][0]['id'], str(to_follow.id))

    def test_dataset_api_list_with_filters(self):
        '''Should filters datasets results based on query filters'''
        owner = UserFactory()
        org = OrganizationFactory()

        [VisibleDatasetFactory() for i in range(2)]

        tag_dataset = VisibleDatasetFactory(tags=['my-tag', 'other'])
        license_dataset = VisibleDatasetFactory(license=LicenseFactory(id='cc-by'))
        format_dataset = DatasetFactory(resources=[ResourceFactory(format='my-format')])
        featured_dataset = VisibleDatasetFactory(featured=True)

        paca, _, _ = create_geozones_fixtures()
        geozone_dataset = VisibleDatasetFactory(spatial=SpatialCoverageFactory(zones=[paca.id]))
        granularity_dataset = VisibleDatasetFactory(spatial=SpatialCoverageFactory(granularity='country'))

        temporal_coverage = db.DateRange(start='2022-05-03', end='2022-05-04')
        temporal_coverage_dataset = DatasetFactory(temporal_coverage=temporal_coverage)

        owner_dataset = VisibleDatasetFactory(owner=owner)
        org_dataset = VisibleDatasetFactory(organization=org)

        schema_dataset = VisibleDatasetFactory(resources=[
            ResourceFactory(schema={'name': 'my-schema', 'version': '1.0.0'})
        ])
        schema_version2_dataset = VisibleDatasetFactory(resources=[
            ResourceFactory(schema={'name': 'other-schema', 'version': '2.0.0'})
        ])

        # filter on tag
        response = self.get(url_for('apiv2.list_datasets', tag='my-tag'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(tag_dataset.id))

        # filter on format
        response = self.get(url_for('apiv2.list_datasets', format='my-format'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(format_dataset.id))

        # filter on featured
        response = self.get(url_for('apiv2.list_datasets', featured='true'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(featured_dataset.id))

        # filter on license
        response = self.get(url_for('apiv2.list_datasets', license='cc-by'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(license_dataset.id))

        # filter on geozone
        response = self.get(url_for('apiv2.list_datasets', geozone=paca.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(geozone_dataset.id))

        # filter on granularity
        response = self.get(url_for('apiv2.list_datasets', granularity='country'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(granularity_dataset.id))

        # filter on temporal_coverage
        response = self.get(url_for('apiv2.list_datasets', temporal_coverage='2022-05-03-2022-05-04'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(temporal_coverage_dataset.id))

        # filter on owner
        response = self.get(url_for('apiv2.list_datasets', owner=owner.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(owner_dataset.id))

        # filter on organization
        response = self.get(url_for('apiv2.list_datasets', organization=org.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(org_dataset.id))

        # filter on schema
        response = self.get(url_for('apiv2.list_datasets', schema='my-schema'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(schema_dataset.id))

        # filter on schema version
        response = self.get(url_for('apiv2.list_datasets', schema_version='2.0.0'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(schema_version2_dataset.id))

    def test_dataset_api_create(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.as_dict()
        self.login()
        response = self.post(url_for('apiv2.create_dataset'), data)
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

        response = self.post(url_for('apiv2.create_dataset'), data)
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
        response = self.post(url_for('apiv2.create_dataset'), data)
        self.assert400(response)
        self.assertEqual(Dataset.objects.count(), 0)

    def test_dataset_api_create_tags(self):
        '''It should create a dataset from the API with tags'''
        data = DatasetFactory.as_dict()
        data['tags'] = [unique_string(16) for _ in range(3)]
        with self.api_user():
            response = self.post(url_for('apiv2.create_dataset'), data)
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
            response = self.post(url_for('apiv2.create_dataset'), data)
        self.assertStatus(response, 400)

    def test_dataset_api_fail_to_create_too_long_tags(self):
        '''Should fail creating a dataset with a tag long'''
        data = DatasetFactory.as_dict()
        data['tags'] = [unique_string(MAX_TAG_LENGTH + 1)]
        with self.api_user():
            response = self.post(url_for('apiv2.create_dataset'), data)
        self.assertStatus(response, 400)

    def test_dataset_api_create_and_slugify_tags(self):
        '''It should create a dataset from the API and slugify the tags'''
        data = DatasetFactory.as_dict()
        data['tags'] = [' Aaa bBB $$ $$-µ  ']
        with self.api_user():
            response = self.post(url_for('apiv2.create_dataset'), data)
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
            response = self.post(url_for('apiv2.create_dataset'), data)
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
            response = self.post(url_for('apiv2.create_dataset'), data)
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
            response = self.post(url_for('apiv2.create_dataset'), data)
        self.assert400(response)

    def test_dataset_api_create_with_geom(self):
        '''It should create a dataset with resources from the API'''
        data = DatasetFactory.as_dict()
        data['spatial'] = {'geom': SAMPLE_GEOM}

        with self.api_user():
            response = self.post(url_for('apiv2.create_dataset'), data)
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
            response = self.post(url_for('apiv2.create_dataset'), data)
            self.assert201(response)
            self.assertEqual(response.json['frequency'], newFreq)

    def test_get_dataset(self):
        resources = [ResourceFactory() for _ in range(2)]
        dataset = DatasetFactory(resources=resources)

        response = self.get(url_for('apiv2.dataset', dataset=dataset))
        self.assert200(response)
        data = response.json
        assert data['resources']['rel'] == 'subsection'
        assert data['resources']['href'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True)
        assert data['resources']['type'] == 'GET'
        assert data['resources']['total'] == len(resources)
        assert data['community_resources']['rel'] == 'subsection'
        assert data['community_resources']['href'] == url_for('api.community_resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True)
        assert data['community_resources']['type'] == 'GET'
        assert data['community_resources']['total'] == 0


class DatasetResourceAPIV2Test(APITestCase):

    def test_get_specific(self):
        '''Should fetch serialized resource from the API based on rid'''
        resources = [ResourceFactory() for _ in range(7)]
        specific_resource = ResourceFactory(id='817204ac-2202-8b4a-98e7-4284d154d10c', title='my-resource')
        resources.append(specific_resource)
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for('apiv2.resource', rid=specific_resource.id))
        self.assert200(response)
        data = response.json
        assert data['dataset_id'] == str(dataset.id)
        assert data['resource']['id'] == str(specific_resource.id)
        assert data['resource']['title'] == specific_resource.title
        response = self.get(url_for('apiv2.resource', rid='111111ac-1111-1b1a-11e1-1111d111d11c'))
        self.assert404(response)
        com_resource = CommunityResourceFactory()
        response = self.get(url_for('apiv2.resource', rid=com_resource.id))
        self.assert200(response)
        data = response.json
        assert data['dataset_id'] is None
        assert data['resource']['id'] == str(com_resource.id)
        assert data['resource']['title'] == com_resource.title

    def test_get(self):
        '''Should fetch 1 page of resources from the API'''
        resources = [ResourceFactory() for _ in range(7)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == len(resources)
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] is None

    def test_get_missing_param(self):
        '''Should fetch 1 page of resources from the API using its default parameters'''
        resources = [ResourceFactory() for _ in range(7)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for('apiv2.resources', dataset=dataset.id))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == len(resources)
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] is None

    def test_get_next_page(self):
        '''Should fetch 2 pages of resources from the API'''
        resources = [ResourceFactory() for _ in range(40)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == DEFAULT_PAGE_SIZE
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=2, page_size=DEFAULT_PAGE_SIZE, _external=True)
        assert data['previous_page'] is None

        response = self.get(data['next_page'])
        self.assert200(response)
        data = response.json
        assert data['total'] == len(resources)
        assert data['page'] == 2
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True)

    def test_get_specific_type(self):
        '''Should fetch resources of type main from the API'''
        nb_resources__of_specific_type = 40
        resources = [ResourceFactory() for _ in range(40)]
        resources += [ResourceFactory(type='main') for _ in range(nb_resources__of_specific_type)]
        dataset = DatasetFactory(resources=resources)
        # Try without resource type filter
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == DEFAULT_PAGE_SIZE
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=2, page_size=DEFAULT_PAGE_SIZE, _external=True)
        assert data['previous_page'] is None

        # Try with resource type filter
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, type='main'))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == DEFAULT_PAGE_SIZE
        assert data['total'] == nb_resources__of_specific_type
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=2, page_size=DEFAULT_PAGE_SIZE, type='main', _external=True)
        assert data['previous_page'] is None

        response = self.get(data['next_page'])
        self.assert200(response)
        data = response.json
        assert data['total'] == nb_resources__of_specific_type
        assert data['page'] == 2
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, type='main', _external=True)

    def test_get_with_query_string(self):
        '''Should fetch resources according to query string from the API'''
        nb_resources_with_specific_title = 20
        resources = [ResourceFactory() for _ in range(40)]
        for i in range(nb_resources_with_specific_title):
            resources += [ResourceFactory(title='primary-{0}'.format(i)) if i % 2 else ResourceFactory(title='secondary-{0}'.format(i))]
        dataset = DatasetFactory(resources=resources)

        # Try without query string filter
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == DEFAULT_PAGE_SIZE
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=2, page_size=DEFAULT_PAGE_SIZE, _external=True)
        assert data['previous_page'] is None

        # Try with query string filter
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, q='primary'))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == 10
        assert data['total'] == 10
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] is None
        assert data['previous_page'] is None

        # Try with query string filter to check case-insensitivity
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, q='PriMarY'))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == 10
        assert data['total'] == 10
        assert data['page'] == 1
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] is None
        assert data['previous_page'] is None
