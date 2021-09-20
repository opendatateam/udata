from flask import url_for
import pytest

from udata.tests.api import APITestCase

from udata.core.dataset.apiv2 import DEFAULT_PAGE_SIZE
from udata.core.dataset.factories import (
    DatasetFactory, ResourceFactory)


class DatasetAPIV2Test(APITestCase):

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
        resources = [ResourceFactory() for _ in range(80)]
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
        assert len(data['data']) == len(resources) - DEFAULT_PAGE_SIZE
        assert data['total'] == len(resources)
        assert data['page'] == 2
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True)

    def test_get_specific_type(self):
        '''Should fetch resources of type main from the API'''
        nb_resources__of_specific_type = 80
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
        assert len(data['data']) == nb_resources__of_specific_type - DEFAULT_PAGE_SIZE
        assert data['total'] == nb_resources__of_specific_type
        assert data['page'] == 2
        assert data['page_size'] == DEFAULT_PAGE_SIZE
        assert data['next_page'] == None
        assert data['previous_page'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE, type='main', _external=True)
