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


def produce(id, message_type, document=None, **kwargs):
    '''
    Produce message with marshalled document.
    kwargs is meant to contain non generic values
    for the meta fields of the message.

    UDATA_INSTANCE_NAME is used as prefix for topic
    '''
    if current_app.config.get('KAFKA_URI'):
        producer = KafkaProducerSingleton.get_instance()
        key = id.encode("utf-8")

        value = {
            'service': 'udata',
            'data': document,
            'meta': {
                'message_type': message_type
            }
        }
        value['meta'].update(kwargs)

        topic = f"{current_app.config['UDATA_INSTANCE_NAME']}.{message_type}"

        producer.send(topic, value=value, key=key)
        producer.flush()
