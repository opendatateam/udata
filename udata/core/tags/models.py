import logging

from mongoengine.fields import DictField, IntField, StringField

from udata.mongo.document import UDataDocument as Document

log = logging.getLogger(__name__)


__all__ = ("Tag",)


class Tag(Document):
    """
    This collection is auto-populated every hour map-reducing tag properties
    from Datasets dans Reuses.
    """

    name = StringField(required=True, unique=True)
    counts = DictField()
    total = IntField(default=0)

    meta = {
        "indexes": ["name", "-total"],
        "ordering": [
            "-total",
        ],
    }

    def clean(self):
        self.total = sum(self.counts.values())
