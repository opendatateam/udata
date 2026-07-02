from mongoengine import EmbeddedDocument

from udata.api_fields import field, generate_fields
from udata.mongo.uuid_fields import AutoUUIDField


# `Bloc` lives in its own module (separate from sibling subclasses like
# `DatasetsListBloc`) so that `organization.models` can depend on the abstract
# base without dragging in `dataservices`/`dataset`/`reuse` at import time —
# which would create a circular import via `dataset.api_fields → Organization`.
@generate_fields()
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))
