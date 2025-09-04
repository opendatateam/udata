import logging
from enum import Enum

from mongoengine.fields import BaseField

log = logging.getLogger(__name__)


class StringEnumField(BaseField):
    """
    Store StrEnum-like enums as plain strings
    """

    def __init__(self, enum_class: type[Enum], **kwargs):
        self.enum_class = enum_class
        super().__init__(choices=list(enum_class), **kwargs)

    def to_python(self, value) -> Enum | None:
        return value if isinstance(value, Enum) else self.enum_class(value)

    def to_mongo(self, value) -> str | None:
        return str(value) if value else None
