from flask import current_app
import pytest
from unittest.mock import patch
from udata.core.dataset.models import Schema

from udata.models import Dataset
from udata.tests.helpers import assert_emit
from udata.core.dataset.events import serialize_resource_for_event
from udata.core.dataset.factories import ResourceFactory, DatasetFactory
from requests.compat import json as complexjson

@pytest.mark.usefixtures('clean_db')
@pytest.mark.usefixtures('enable_resource_event')
class DatasetEventsTest:

    @patch('requests.post')
    def test_publish_message_resource_created(self, mock_req):
        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        expected_value = {
            'resource_id': str(resource.id),
            'dataset_id': str(dataset.id),
            'document': serialize_resource_for_event(resource)
        }

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/created/",
                                    json=expected_value)

    @patch('requests.post')
    def test_publish_message_resource_modified(self, mock_req):
        resource = ResourceFactory(schema=Schema(url="http://localhost/my-schema"))
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = 'New description'

        expected_value = {
            'resource_id': str(resource.id),
            'dataset_id': str(dataset.id),
            'document': serialize_resource_for_event(resource)
        }

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/updated/",
                                    json=expected_value)
        
        # Mocking requests call doesn't call the JSON encoder
        # so calling it manually here to prevent encoding errors.
        # (for example, encoding Embeds fails)
        complexjson.dumps(expected_value)

    @patch('requests.post')
    def test_publish_message_resource_removed(self, mock_req):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_removed,)

        expected_value = {
            'resource_id': str(resource.id),
            'dataset_id': str(dataset.id),
            'document': None
        }

        with assert_emit(*expected_signals):
            dataset.remove_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/deleted/",
                                    json=expected_value)
