import logging
from enum import StrEnum

from mongoengine.fields import BaseField

log = logging.getLogger(__name__)


class StrEnumField(BaseField):
    """
    Store StrEnum as plain strings
    """

    def __init__(self, enum_class: type[StrEnum], **kwargs):
        self.enum_class = enum_class
        super().__init__(choices=list(enum_class), **kwargs)

    def to_python(self, value) -> StrEnum:
        return self.enum_class(value)
