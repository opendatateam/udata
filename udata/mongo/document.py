import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar, Generic

from mongoengine.errors import NotUniqueError
from typing_extensions import TypeVar

from udata.flask_mongoengine.document import Document

from .queryset import UDataQuerySet

if TYPE_CHECKING:
    from bson import ObjectId

QS = TypeVar("QS", bound=UDataQuerySet, default=UDataQuerySet)

log = logging.getLogger(__name__)

MAX_SLUG_SAVE_ATTEMPTS = 5


def serialize(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    elif isinstance(value, dict):
        return {key: serialize(val) for key, val in value.items()}
    elif isinstance(value, Iterable) and not isinstance(value, str):
        return [serialize(val) for val in value]
    else:
        return value


def get_all_models():
    from udata import models as core_models
    from udata.api import oauth2 as oauth2_models
    from udata.harvest import models as harvest_models

    all_models = set()
    for models in core_models, harvest_models, oauth2_models:
        for model in models.__dict__.values():
            if isinstance(model, type) and issubclass(model, (UDataDocument)):
                all_models.add(model)

    return all_models


class UDataDocument(Document, Generic[QS]):
    meta = {
        "abstract": True,
        "queryset_class": UDataQuerySet,
    }

    # Dynamically created by MongoEngine's metaclass, declared here for type checkers.
    objects: QS
    DoesNotExist: ClassVar[type[Exception]]
    id: "ObjectId"

    def save(self, *args, **kwargs):
        # A SlugField picks a free suffix by querying the collection, which leaves a window
        # for a concurrent writer to insert that very slug before we do. No client-side check
        # can close that window, so replay the save instead: the pre_save signal will look
        # for the next free suffix, this time against the slug the other writer just took.
        # Imported here because `slug_fields` is built on top of this module.
        from .slug_fields import conflicting_slug_fields, reset_slug

        for attempt in range(MAX_SLUG_SAVE_ATTEMPTS):
            try:
                return super().save(*args, **kwargs)
            except NotUniqueError as error:
                conflicting = conflicting_slug_fields(self, error)
                if not conflicting or attempt == MAX_SLUG_SAVE_ATTEMPTS - 1:
                    raise
                for field in conflicting:
                    log.info(
                        "Slug %s was taken concurrently on %s, regenerating it",
                        getattr(self, field.db_field),
                        self.__class__.__name__,
                    )
                    reset_slug(self, field)

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
