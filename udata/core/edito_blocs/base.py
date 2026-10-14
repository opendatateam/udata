from mongoengine import EmbeddedDocument
from mongoengine.base.datastructures import BaseList
from mongoengine.fields import EmbeddedDocumentListField, ListField, ReferenceField

from udata.api_fields import field, generate_fields
from udata.mongo.uuid_fields import AutoUUIDField

# List fields (references or embedded documents) that no bloc card displays (the card masks
# live in `models.py`). Loading them is pure waste: `select_related` would dereference a
# reuse's `datasets`/`dataservices` lists (and a dataset's `contact_points`) one document per
# item, and a dataset's `resources` list deserializes dozens of embedded sub-documents — all
# for data the card never serializes. That work, not the queries, dominates the response
# time, so we drop these from the load query. Each is excluded only on models that have it.
#
# Why hardcode this instead of deriving it from the card masks? The masks are *include*
# lists ("show these fields"), but a Mongo projection here needs the opposite: which heavy
# fields to *exclude* from the load. Inverting one isn't a free `.only(mask)` either — the
# masks list display names (`quality`, `page`, `uri`…) that don't map 1:1 to stored fields
# (`quality_cached`, computed properties…), so a load projection can't be read straight off
# them.
CARD_UNUSED_HEAVY_FIELDS = (
    "resources",  # Dataset: embedded list of resources
    "datasets",  # Reuse / Dataservice: referenced datasets
    "dataservices",  # Reuse: referenced dataservices
    "contact_points",  # Dataset / Dataservice: referenced contact points
    "access_audiences",  # Dataset / Dataservice: embedded access audiences
)


def prefetch_blocs_references(blocs):
    """Batch-load the datasets/reuses/dataservices referenced by a list of blocs.

    Declared as the `prefetch` of `Bloc`, so it runs on every bloc list about to be
    marshalled — and only on those: a field the response mask excludes is never read.

    Marshalling blocs serializes each referenced object as a card including its
    `organization` (and `owner`). MongoEngine dereferences each reference — and each
    reference's own organization/owner — one query at a time, with no cross-instance
    cache. A page with dozens of cards therefore triggers hundreds of sequential
    queries (one per organization), which dominates the response time.

    We collect every reference across the whole (possibly accordion-nested) bloc tree,
    reload each type as a single flat query with `select_related` (which batches the
    organization/owner lookups), and inject the resolved documents back into the blocs.
    Marshalling then issues no further query.

    The load query also drops the heavy fields no card shows (a dataset's `resources`),
    so we stop paying to deserialize data that isn't serialized — the dominant cost on
    real pages. See `CARD_UNUSED_HEAVY_FIELDS`.

    This runs once per marshalled bloc list — including the nested ones, since an
    accordion item's `content` is a bloc list of its own. The top-level call already
    walked the whole tree, so lists it resolved are skipped when their own field is
    marshalled in turn.
    """
    # (bloc, attr, model, [referenced ids]) for every bloc holding references.
    collected: list[tuple] = []

    def walk(blocs):
        for bloc in blocs:
            for attr, mongo_field in type(bloc)._fields.items():
                if isinstance(mongo_field, ListField) and isinstance(
                    mongo_field.field, ReferenceField
                ):
                    # A `ListField(ReferenceField)`: read the raw references from `_data`
                    # to avoid a per-bloc dereference (we batch them across all blocs).
                    refs = bloc._data.get(attr)
                    if not refs or getattr(refs, "_dereferenced", False):
                        # Nothing to load, or a nested list an outer call already
                        # resolved (see the docstring on re-entrance).
                        continue
                    model = mongo_field.field.document_type
                    collected.append((bloc, attr, model, [ref.id for ref in refs]))
                elif isinstance(mongo_field, EmbeddedDocumentListField):
                    # Recurse into nested blocs (e.g. accordion items -> content).
                    walk(getattr(bloc, attr) or [])

    walk(blocs)

    ids_by_model: dict = {}
    for _, _, model, ids in collected:
        ids_by_model.setdefault(model, set()).update(ids)

    docs_by_model = {}
    for model, ids in ids_by_model.items():
        unused = [f for f in CARD_UNUSED_HEAVY_FIELDS if f in model._fields]
        queryset = model.objects(id__in=list(ids)).exclude(*unused).select_related()
        docs_by_model[model] = {doc.id: doc for doc in queryset}

    for bloc, attr, model, ids in collected:
        by_id = docs_by_model[model]
        # Mark the list as already dereferenced so marshalling reads it as-is instead
        # of dereferencing each reference (and its organization) again.
        resolved = BaseList([by_id[ref_id] for ref_id in ids if ref_id in by_id], bloc, attr)
        resolved._dereferenced = True
        bloc._data[attr] = resolved


# `Bloc` lives in its own module (separate from sibling subclasses like
# `DatasetsListBloc`) so that `organization.models` can depend on the abstract
# base without dragging in `dataservices`/`dataset`/`reuse` at import time —
# which would create a circular import via `dataset.api_fields → Organization`.
@generate_fields(prefetch=prefetch_blocs_references)
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))
