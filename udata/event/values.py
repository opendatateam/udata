from enum import Enum


class KafkaMessageType(Enum):
    INDEX = 'index'
    REINDEX = 'reindex'
    UNINDEX = 'unindex'
    RESOURCE_CREATED = 'resource_created'
    RESOURCE_MODIFIED = 'resource_modified'
    RESOURCE_DELETED = 'resource_removed'


class KafkaTopic(Enum):
    RESOURCE_CREATED = 'resource.created'
    RESOURCE_MODIFIED = 'resource.modified'
    RESOURCE_DELETED = 'resource.removed'
