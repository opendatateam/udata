from flask import url_for
import pytest

from udata.tests.api import APITestCase

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
        assert data['resources']['href'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size= 20, _external=True)
        assert data['resources']['type'] == 'GET'
        assert data['resources']['total'] == len(resources)
        assert data['community_resources']['rel'] == 'subsection'
        assert data['community_resources']['href'] == url_for('api.community_resources', dataset=dataset.id, page=1, page_size= 20, _external=True)
        assert data['community_resources']['type'] == 'GET'
        assert data['community_resources']['total'] == 0


class DatasetResourceAPIV2Test(APITestCase):

    def test_get(self):
        '''Should fetch paginated resources from the API'''
        resources = [ResourceFactory() for _ in range(7)]
        dataset = DatasetFactory(resources=resources)
        page_size = 5
        response = self.get(url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=page_size))
        self.assert200(response)
        data = response.json
        assert len(data['data']) == page_size
        assert data['total'] == len(resources)
        assert data['page'] == 1
        assert data['page_size'] == page_size
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=2, page_size=page_size, _external=True)
        assert data['previous_page'] is None

        response = self.get(data['next_page'])
        self.assert200(response)
        data = response.json
        assert len(data['data']) == 2
        assert data['total'] == len(resources)
        assert data['page'] == 2
        assert data['page_size'] == page_size
        assert data['next_page'] == url_for('apiv2.resources', dataset=dataset.id, page=3, page_size=page_size, _external=True)
        assert data['previous_page'] == url_for('apiv2.resources', dataset=dataset.id, page=1, page_size=page_size, _external=True)
