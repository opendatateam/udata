from enum import Enum


class EventMessageType(Enum):
    INDEX = "index"
    REINDEX = "reindex"
    UNINDEX = "unindex"
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
