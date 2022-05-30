import logging

from udata.commands import cli

from .consumer import EventConsumerSingleton
log = logging.getLogger(__name__)


@cli.group('event')
def grp():
    '''Event operations'''
    pass


@grp.command()
def consume():
    '''Consume event messages'''
    log.info('Consume event messages')
    event_consumer = EventConsumerSingleton.get_instance()
    event_consumer.consume_kafka_messages()
