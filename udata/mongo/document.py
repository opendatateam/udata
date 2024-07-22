import logging
from collections.abc import Iterable

from flask_mongoengine import Document

from .queryset import UDataQuerySet

log = logging.getLogger(__name__)


def serialize(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    elif isinstance(value, dict):
        return {key: serialize(val) for key, val in value.items()}
    elif isinstance(value, Iterable) and not isinstance(value, str):
        return [serialize(val) for val in value]
    else:
        return value


class UDataDocument(Document):
    meta = {
        "abstract": True,
        "queryset_class": UDataQuerySet,
    }

    def to_dict(self, exclude=None):
        id_field = self._meta["id_field"]
        excluded_keys = set(exclude or [])
        excluded_keys.add("_id")
        excluded_keys.add("_cls")
        data = dict(
            (
                (key, serialize(value))
                for key, value in self.to_mongo().items()
                if key not in excluded_keys
            )
        )
        data[id_field] = getattr(self, id_field)
        return data

    def __str__(self):
        return "{classname}({id})".format(
            classname=self.__class__.__name__, id=getattr(self, self._meta["id_field"])
        )


class DomainModel(UDataDocument):
    """Placeholder for inheritance"""

    pass
