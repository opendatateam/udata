import json
from flask import current_app
from kafka import KafkaProducer
from udata.models import db, Dataset, Organization, Reuse


class KafkaProducerSingleton:
    __instance = None

    @staticmethod
    def get_instance() -> KafkaProducer:
        if KafkaProducerSingleton.__instance is None:
            KafkaProducerSingleton.__instance = KafkaProducer(
                bootstrap_servers=current_app.config.get('KAFKA_URI'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        return KafkaProducerSingleton.__instance


def produce(model, id, message_type, document=None, index=None):
    '''Produce message with marshalled document'''
    producer = KafkaProducerSingleton.get_instance()
    key = id.encode("utf-8")
    if model == Dataset:
        topic = 'dataset'
    if model == Organization:
        topic = 'organization'
    if model == Reuse:
        topic = 'reuse'
    if not topic:
        return

    if not index:
        index = topic
    value = {
        'service': 'udata',
        'data': document,
        'meta': {
            'message_type': message_type.value,
            'index': index
        }
    }

    producer.send(topic, value=value, key=key)
    producer.flush()
