from enum import Enum


class KafkaMessageType(Enum):
    INDEX = 'index'
    REINDEX = 'reindex'
    UNINDEX = 'unindex'
    CREATED = 'created'
    MODIFIED = 'modified'
    DELETED = 'deleted'
