from typing import NamedTuple

from bson import ObjectId
from mongoengine import EmbeddedDocument
from mongoengine.base.datastructures import BaseList
from mongoengine.fields import EmbeddedDocumentListField, ListField, ReferenceField, StringField

from udata.api_fields import field, generate_fields
from udata.mongo.errors import FieldValidationError
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


class SingleReference(NamedTuple):
    """A bloc showing a single object, as collected by `prefetch_blocs_references`."""

    holder: list
    bloc: EmbeddedDocument
    attr: str
    model: type
    id: ObjectId


class Container(NamedTuple):
    """A bloc (section, accordion item) holding a list of blocs, and the list holding it."""

    holder: list
    bloc: EmbeddedDocument


class ListOfReferences(NamedTuple):
    """A legacy bloc listing several objects, as collected by `prefetch_blocs_references`."""

    bloc: EmbeddedDocument
    attr: str
    model: type
    ids: list[ObjectId]


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

    A bloc showing a single object that no longer exists is left out, with the containers
    it leaves empty (section, accordion item). Nothing purges the blocs of a hard-deleted
    object from storage: they go when the page is saved again, from what it read.

    This runs once per marshalled bloc list — including the nested ones, since a
    section's `blocs` or an accordion item's `content` is a bloc list of its own. The top-level
    call already walked the whole tree and marked the blocs it went through, so they are
    skipped when their own list is marshalled in turn.
    """
    collected: list[ListOfReferences] = []
    collected_single: list[SingleReference] = []
    # Each container, by the id of the list it contains
    containers: dict[int, Container] = {}

    def walk(blocs):
        for bloc in blocs:
            if getattr(bloc, "_blocs_prefetched", False):
                continue
            bloc._blocs_prefetched = True
            for attr, mongo_field in type(bloc)._fields.items():
                if isinstance(mongo_field, ReferenceField):
                    # A `DBRef`, or a document MongoEngine already dereferenced (without its
                    # organization/owner) when the blocs list holding it was read.
                    ref = bloc._data.get(attr)
                    if ref is not None:
                        collected_single.append(
                            SingleReference(blocs, bloc, attr, mongo_field.document_type, ref.id)
                        )
                elif isinstance(mongo_field, ListField) and isinstance(
                    mongo_field.field, ReferenceField
                ):
                    # A `ListField(ReferenceField)`: read the raw references from `_data`
                    # to avoid a per-bloc dereference (we batch them across all blocs).
                    refs = bloc._data.get(attr)
                    if refs:
                        model = mongo_field.field.document_type
                        collected.append(
                            ListOfReferences(bloc, attr, model, [ref.id for ref in refs])
                        )
                elif isinstance(mongo_field, EmbeddedDocumentListField):
                    # Recurse into nested blocs (e.g. accordion items -> content). Read from `_data`:
                    # reading the attribute would dereference the list's references on its
                    # own, one query per list.
                    nested = bloc._data.get(attr)
                    if nested:
                        containers[id(nested)] = Container(blocs, bloc)
                        walk(nested)

    def remove(holder: list, item: EmbeddedDocument):
        # By identity: two blocs can be equal (same object shown twice).
        del holder[next(i for i, held in enumerate(holder) if held is item)]
        if not holder and id(holder) in containers:
            container = containers[id(holder)]
            remove(container.holder, container.bloc)

    walk(blocs)

    ids_by_model: dict = {}
    for references in collected:
        ids_by_model.setdefault(references.model, set()).update(references.ids)
    for reference in collected_single:
        ids_by_model.setdefault(reference.model, set()).add(reference.id)

    docs_by_model = {}
    for model, ids in ids_by_model.items():
        unused = [f for f in CARD_UNUSED_HEAVY_FIELDS if f in model._fields]
        queryset = model.objects(id__in=list(ids)).exclude(*unused).select_related()
        docs_by_model[model] = {doc.id: doc for doc in queryset}

    for references in collected:
        by_id = docs_by_model[references.model]
        # Mark the list as already dereferenced so marshalling reads it as-is instead
        # of dereferencing each reference (and its organization) again.
        resolved = BaseList(
            [by_id[ref_id] for ref_id in references.ids if ref_id in by_id],
            references.bloc,
            references.attr,
        )
        resolved._dereferenced = True
        references.bloc._data[references.attr] = resolved

    for reference in collected_single:
        document = docs_by_model[reference.model].get(reference.id)
        if document is None:
            remove(reference.holder, reference.bloc)
        else:
            reference.bloc._data[reference.attr] = document


BLOC_WIDTHS = ("1/4", "1/3", "1/2", "2/3", "3/4", "1")


# `Bloc` lives in its own module (separate from sibling subclasses like
# `DatasetBloc`) so that `organization.models` can depend on the abstract
# base without dragging in `dataservices`/`dataset`/`reuse` at import time —
# which would create a circular import via `dataset.api_fields → Organization`.
@generate_fields(prefetch=prefetch_blocs_references)
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))
    width = field(
        StringField(choices=BLOC_WIDTHS),
        description="Share of the row taken by the bloc inside a section or an accordion item, "
        "the next blocs wrapping to a new row when it is full. Without it, the whole row.",
    )


# The layout of a blocs field, from the top: heroes and sections; sections hold accordions
# and leaves, accordion items only hold leaves.
LEAF_BLOCS = {
    "TitleBloc",
    "MarkdownBloc",
    "LinksListBloc",
    "ExploreBloc",
    "DatasetBloc",
    "ReuseBloc",
    "DataserviceBloc",
}
TOP_LEVEL_BLOCS = {"HeroBloc", "SectionBloc"}
SECTION_BLOCS = LEAF_BLOCS | {"AccordionListBloc"}
# The explorer is too wide for an accordion.
ACCORDION_BLOCS = LEAF_BLOCS - {"ExploreBloc"}

# Fields of the legacy format that must stay empty (see `BlocWithTitleMixin`).
LEGACY_TITLE_FIELDS = ("title", "subtitle", "description")
BLOCS_WITH_LEGACY_TITLE = {"MarkdownBloc", "LinksListBloc", "ExploreBloc", "AccordionListBloc"}


def _check_layout(blocs, allowed: set, field: str):
    for bloc in blocs:
        name = bloc.__class__.__name__
        if name not in allowed:
            raise FieldValidationError(
                field=field,
                message=f"{name} is not allowed here, expected one of {sorted(allowed)}",
            )
        if name in BLOCS_WITH_LEGACY_TITLE and any(
            getattr(bloc, f, None) for f in LEGACY_TITLE_FIELDS
        ):
            raise FieldValidationError(
                field=field, message=f"{name} cannot have a title, use a TitleBloc"
            )
        if allowed is TOP_LEVEL_BLOCS and bloc.width:
            raise FieldValidationError(
                field=field, message=f"{name} spans the whole page, it cannot have a width"
            )
        if name == "SectionBloc":
            _check_layout(bloc.blocs, SECTION_BLOCS, field)
        elif name == "AccordionListBloc":
            for item in bloc.items:
                _check_layout(item.content, ACCORDION_BLOCS, field)


def check_blocs_layout(blocs, field, **_kwargs):
    _check_layout(blocs or [], TOP_LEVEL_BLOCS, field)
