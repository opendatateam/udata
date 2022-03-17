from enum import Enum
from .producer import produce, KafkaProducerSingleton # noqa


class KafkaMessageType(Enum):
    INDEX = 'index'
    REINDEX = 'reindex'
    UNINDEX = 'unindex'
