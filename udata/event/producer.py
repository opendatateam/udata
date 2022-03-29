import json
from flask import current_app
from kafka import KafkaProducer


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


def produce(topic, id, message_type, document=None, **kwargs):
    '''
    Produce message with marshalled document.
    kwargs is meant to contain non generic values
    for the meta fields of the message.
    '''
    producer = KafkaProducerSingleton.get_instance()
    key = id.encode("utf-8")

    value = {
        'service': 'udata',
        'data': document,
        'meta': {
            'message_type': message_type.value
        }
    }
    value['meta'].update(kwargs)

    producer.send(topic, value=value, key=key)
    producer.flush()
