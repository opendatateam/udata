import logging

from flask import current_app

from udata_event_service.consumer import consume_kafka

from udata.core.dataset.event import (
    consume_message_resource_analysed,
    consume_message_resource_stored,
    consume_message_resource_checked
)
from .producer import get_topic

log = logging.getLogger(__name__)


class EventConsumerSingleton():
    registered = {}
    topics = set()

    __instance = None

    @staticmethod
    def get_instance():
        if EventConsumerSingleton.__instance is None:
            EventConsumerSingleton.__instance = EventConsumerSingleton()
        return EventConsumerSingleton.__instance

    def register(self, topics, message_types, function):
        '''Register topics, message types and corresponding callable'''
        if not callable(function):
            msg = 'ExtrasField can only register callables'
            raise TypeError(msg)
        for message_type in message_types:
            self.registered[message_type] = function
        self.topics.update(topics)

    def route_messages(self, key, data, **kwargs):
        try:
            log.debug(f'Consume message {key}')
            message_type = data['meta']['message_type']
            function = self.registered.get(message_type)
            if function:
                function(key, data)
            else:
                log.warn(f'no consumer for the message type {message_type} on this topic')

        except Exception as e:  # Catch and deal with exceptions accordingly
            log.error(f'Error when consuming message {key}: {e}')
            pass

    def consume_kafka_messages(self):
        if self.topics:
            consume_kafka(
                kafka_uri=current_app.config['KAFKA_URI'],
                group_id='udata',
                topics=self.topics,
                message_processing_func=self.route_messages,
            )
        else:
            log.warn('No topics to listen to, exiting.')


# TODO: where to register?
event_consumer = EventConsumerSingleton.get_instance()
event_consumer.register(
    topics=['udata.resource.analysed'],
    message_types=['resource.analysed'],
    function=consume_message_resource_analysed
)
event_consumer.register(
    topics=['udata.resource.stored'],
    message_types=['resource.stored'],
    function=consume_message_resource_stored
)
event_consumer.register(
    topics=['udata.resource.checked'],
    message_types=['event-update', 'initialization', 'regular-update'],
    function=consume_message_resource_checked
)
