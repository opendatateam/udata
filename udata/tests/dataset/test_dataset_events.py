from flask import current_app
import pytest
from unittest.mock import Mock

from udata.models import Dataset
from udata.tests.helpers import assert_emit
from udata_event_service.producer import KafkaProducerSingleton
from udata.core.dataset.events import serialize_resource_for_event
from udata.core.dataset.factories import ResourceFactory, DatasetFactory
from udata.event.values import KafkaMessageType


@pytest.mark.usefixtures('clean_db')
@pytest.mark.usefixtures('enable_resource_event')
@pytest.mark.usefixtures('enable_kafka')
class DatasetEventsTest:

    def test_publish_message_resource_created(self):
        KafkaProducerSingleton.get_instance = Mock()

        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        producer = KafkaProducerSingleton.get_instance(None)
        message_type = f'resource.{KafkaMessageType.CREATED.value}'

        expected_value = {
            'service': 'udata',
            'value': serialize_resource_for_event(resource),
            'meta': {
                'message_type': message_type,
                'dataset_id': str(dataset.id)
            }
        }
        topic = f"{current_app.config['UDATA_INSTANCE_NAME']}.{message_type}"
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))

    def test_publish_message_resource_modified(self):
        KafkaProducerSingleton.get_instance = Mock()

        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = 'New description'

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)

        producer = KafkaProducerSingleton.get_instance(None)
        message_type = f'resource.{KafkaMessageType.MODIFIED.value}'

        expected_value = {
            'service': 'udata',
            'value': serialize_resource_for_event(resource),
            'meta': {
                'message_type': message_type,
                'dataset_id': str(dataset.id)
            }
        }
        topic = f"{current_app.config['UDATA_INSTANCE_NAME']}.{message_type}"
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))

    def test_publish_message_resource_removed(self):
        KafkaProducerSingleton.get_instance = Mock()

        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_removed,)

        with assert_emit(*expected_signals):
            dataset.remove_resource(resource)

        producer = KafkaProducerSingleton.get_instance(None)
        message_type = f'resource.{KafkaMessageType.DELETED.value}'

        expected_value = {
            'service': 'udata',
            'value': None,
            'meta': {
                'message_type': message_type,
                'dataset_id': str(dataset.id)
            }
        }
        topic = f"{current_app.config['UDATA_INSTANCE_NAME']}.{message_type}"
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))
