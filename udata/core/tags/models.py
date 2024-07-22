import logging

from udata.mongo import db

log = logging.getLogger(__name__)


__all__ = ("Tag",)


class Tag(db.Document):
    """
    This collection is auto-populated every hour map-reducing tag properties
    from Datasets dans Reuses.
    """

    name = db.StringField(required=True, unique=True)
    counts = db.DictField()
    total = db.IntField(default=0)

    meta = {
        "indexes": ["name", "-total"],
        "ordering": [
            "-total",
        ],
    }

    def clean(self):
        self.total = sum(self.counts.values())
