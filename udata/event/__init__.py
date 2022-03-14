from enum import Enum
from .producer import produce, KafkaProducerSingleton


class KafkaMessageType(Enum):
    INDEX = 'index'
    REINDEX = 'reindex'
    UNINDEX = 'unindex'
