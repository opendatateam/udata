from flask import current_app
import pytest
from unittest.mock import patch

from udata.models import Dataset
from udata.tests.helpers import assert_emit
from udata.core.dataset.events import serialize_resource_for_event
from udata.core.dataset.factories import ResourceFactory, DatasetFactory
from udata.event.values import EventMessageType


@pytest.mark.usefixtures('clean_db')
@pytest.mark.usefixtures('enable_resource_event')
class DatasetEventsTest:

    @patch('requests.post')
    def test_publish_message_resource_created(self, mock_req):
        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        message_type = f'resource.{EventMessageType.CREATED.value}'
        expected_value = {
            'key': str(resource.id),
            'document': serialize_resource_for_event(resource),
            'meta': {'message_type': message_type, 'dataset_id': str(dataset.id)}
        }

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/created/",
                                    json=expected_value)

    @patch('requests.post')
    def test_publish_message_resource_modified(self, mock_req):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = 'New description'

        message_type = f'resource.{EventMessageType.MODIFIED.value}'
        expected_value = {
            'key': str(resource.id),
            'document': serialize_resource_for_event(resource),
            'meta': {'message_type': message_type, 'dataset_id': str(dataset.id)}
        }

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/updated/",
                                    json=expected_value)

    @patch('requests.post')
    def test_publish_message_resource_removed(self, mock_req):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_removed,)

        message_type = f'resource.{EventMessageType.DELETED.value}'
        expected_value = {
            'key': str(resource.id),
            'document': None,
            'meta': {'message_type': message_type, 'dataset_id': str(dataset.id)}
        }

        with assert_emit(*expected_signals):
            dataset.remove_resource(resource)

        mock_req.assert_called_with(f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/deleted/",
                                    json=expected_value)
