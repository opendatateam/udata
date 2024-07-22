import logging
import uuid

from mongoengine.fields import UUIDField

log = logging.getLogger(__name__)


class AutoUUIDField(UUIDField):
    """
    An autopopulated UUID field.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("binary", False)
        super(AutoUUIDField, self).__init__(**kwargs)

    def __set__(self, instance, value):
        if not value:
            value = uuid.uuid4()
        return super(AutoUUIDField, self).__set__(instance, value)
