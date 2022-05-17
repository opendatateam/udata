import pytest

from unittest.mock import Mock
from udata.models import Dataset
from udata.tests.helpers import assert_emit
from udata.event import KafkaProducerSingleton
from udata.core.dataset.events import serialize_resource_for_event
from udata.core.dataset.factories import ResourceFactory, DatasetFactory
from udata.event.values import KafkaMessageType, KafkaTopic


@pytest.mark.usefixtures('clean_db')
@pytest.mark.usefixtures('enable_resource_event')
@pytest.mark.usefixtures('enable_kafka')
class DatasetEventsTest:

    def test_publish_message_resource_created(self):
        kafka_mock = Mock()
        KafkaProducerSingleton.get_instance = lambda: kafka_mock

        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        producer = KafkaProducerSingleton.get_instance()

        expected_value = {
            'service': 'udata',
            'data': serialize_resource_for_event(resource),
            'meta': {
                'message_type': KafkaMessageType.RESOURCE_CREATED.value,
                'dataset_id': str(dataset.id)
            }
        }
        producer.send.assert_called_with(KafkaTopic.RESOURCE_CREATED.value, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))

    def test_publish_message_resource_modified(self):
        kafka_mock = Mock()
        KafkaProducerSingleton.get_instance = lambda: kafka_mock

        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = 'New description'

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)

        producer = KafkaProducerSingleton.get_instance()

        expected_value = {
            'service': 'udata',
            'data': serialize_resource_for_event(resource),
            'meta': {
                'message_type': KafkaMessageType.RESOURCE_MODIFIED.value,
                'dataset_id': str(dataset.id)
            }
        }
        producer.send.assert_called_with(KafkaTopic.RESOURCE_MODIFIED.value, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))

    def test_publish_message_resource_removed(self):
        kafka_mock = Mock()
        KafkaProducerSingleton.get_instance = lambda: kafka_mock

        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_removed,)

        with assert_emit(*expected_signals):
            dataset.remove_resource(resource)

        producer = KafkaProducerSingleton.get_instance()

        expected_value = {
            'service': 'udata',
            'data': None,
            'meta': {
                'message_type': KafkaMessageType.RESOURCE_DELETED.value,
                'dataset_id': str(dataset.id)
            }
        }
        producer.send.assert_called_with(KafkaTopic.RESOURCE_DELETED.value, value=expected_value,
                                         key=str(resource.id).encode("utf-8"))
