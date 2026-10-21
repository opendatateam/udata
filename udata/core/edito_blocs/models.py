import uuid

from mongoengine import EmbeddedDocument
from mongoengine.fields import (
    EmbeddedDocumentListField,
    ListField,
    ReferenceField,
    StringField,
    UUIDField,
)

from udata.api import api
from udata.api_fields import classes_by_parents, field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import get_dataset_by_resource_id
from udata.core.edito_blocs.base import Bloc
from udata.core.reuse.models import Reuse
from udata.mongo.errors import FieldValidationError
from udata.mongo.uuid_fields import AutoUUIDField


class BlocWithTitleMixin:
    # Legacy: titles now live in their own `TitleBloc`. Only kept so that blocs saved
    # before the `2026-10-21-blocs-sections` migration still load and serialize;
    # `check_blocs_layout` rejects them on write.
    title = field(StringField())
    subtitle = field(StringField())


DATASET_CARD_MASK = "{id,title,acronym,slug,description,page,uri,private,archived,organization,owner,last_update,quality,metrics,badges,tags}"
dataset_card_fields = api.model("Dataset (card)", dict(dataset_fields), mask=DATASET_CARD_MASK)

REUSE_CARD_MASK = "{id,title,slug,description,type,url,image,image_thumbnail,page,uri,organization,owner,metrics,badges,tags,topic,private,created_at,last_modified}"
reuse_card_fields = api.model("Reuse (card)", dict(Reuse.__read_fields__), mask=REUSE_CARD_MASK)

DATASERVICE_CARD_MASK = "{id,title,acronym,slug,description,base_api_url,format,self_api_url,self_web_url,organization,owner,metrics,badges,tags,private,created_at,metadata_modified_at}"
dataservice_card_fields = api.model(
    "Dataservice (card)", dict(Dataservice.__read_fields__), mask=DATASERVICE_CARD_MASK
)


# Legacy: the `*ListBloc` became a `GridBloc` of `DatasetBloc`/`ReuseBloc`/`DataserviceBloc`.
# Only kept so that blocs saved before the `2026-10-21-blocs-sections` migration still load
# and serialize; `check_blocs_layout` rejects them on write.
@generate_fields()
class DatasetsListBloc(BlocWithTitleMixin, Bloc):
    datasets = field(
        ListField(
            field(
                ReferenceField("Dataset"),
                nested_fields=dataset_card_fields,
            )
        )
    )


@generate_fields()
class ReusesListBloc(BlocWithTitleMixin, Bloc):
    reuses = field(
        ListField(
            field(
                ReferenceField("Reuse"),
                nested_fields=reuse_card_fields,
            )
        )
    )


@generate_fields()
class DataservicesListBloc(BlocWithTitleMixin, Bloc):
    dataservices = field(
        ListField(
            field(
                ReferenceField("Dataservice"),
                nested_fields=dataservice_card_fields,
            )
        )
    )


@generate_fields()
class DatasetBloc(Bloc):
    dataset = field(
        ReferenceField("Dataset", required=True),
        nested_fields=dataset_card_fields,
        # A dataset hard-deleted before `purge_blocs_references` ran reads as null.
        allow_null=True,
    )


@generate_fields()
class ReuseBloc(Bloc):
    reuse = field(
        ReferenceField("Reuse", required=True),
        nested_fields=reuse_card_fields,
        allow_null=True,
    )


@generate_fields()
class DataserviceBloc(Bloc):
    dataservice = field(
        ReferenceField("Dataservice", required=True),
        nested_fields=dataservice_card_fields,
        allow_null=True,
    )


@generate_fields()
class TitleBloc(Bloc):
    title = field(StringField(required=True))
    subtitle = field(StringField())


@generate_fields()
class LinkInBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    color = field(StringField())
    url = field(StringField())


@generate_fields()
class LinksListBloc(BlocWithTitleMixin, Bloc):
    paragraph = field(StringField())
    main_link_url = field(StringField())
    main_link_title = field(StringField())

    links = field(EmbeddedDocumentListField(LinkInBloc))


HERO_COLORS = ("primary", "green", "purple")


@generate_fields()
class HeroBloc(Bloc):
    title = field(StringField(required=True))
    description = field(StringField())
    color = field(StringField(choices=HERO_COLORS))
    main_link_url = field(StringField())
    main_link_title = field(StringField())


@generate_fields()
class MarkdownBloc(BlocWithTitleMixin, Bloc):
    content = field(
        StringField(required=True),
        markdown=True,
    )


def check_resource_exists(resource_id, field, **_kwargs):
    try:
        resource_id = uuid.UUID(str(resource_id))
    except ValueError:
        raise FieldValidationError(field=field, message=f"'{resource_id}' is not a valid UUID")
    if not get_dataset_by_resource_id(resource_id):
        raise FieldValidationError(field=field, message=f"Unknown resource '{resource_id}'")


@generate_fields()
class ExploreBloc(BlocWithTitleMixin, Bloc):
    resource_id = field(
        UUIDField(required=True, binary=False),
        checks=[check_resource_exists],
    )


@generate_fields()
class AccordionItemBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    content = field(EmbeddedDocumentListField(Bloc), generic=True)


@generate_fields()
class AccordionListBloc(Bloc):
    # Legacy, see `BlocWithTitleMixin`.
    title = field(StringField())
    description = field(StringField())
    items = field(EmbeddedDocumentListField(AccordionItemBloc))


GRID_CELL_WIDTHS = ("1/4", "1/3", "1/2", "2/3", "3/4", "1")


@generate_fields()
class GridCell(EmbeddedDocument):
    id = field(AutoUUIDField(primary_key=True))
    width = field(
        StringField(choices=GRID_CELL_WIDTHS),
        description="Share of the row taken by the cell. Without it, the cell takes what the "
        "cells with a width leave, shared with the other cells without one.",
    )
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


@generate_fields()
class GridBloc(Bloc):
    cells = field(EmbeddedDocumentListField(GridCell))


@generate_fields()
class SectionBloc(Bloc):
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


# Where a bloc can sit inside a blocs field, following the layout checked by
# `check_blocs_layout`. The last one is the legacy accordion at the top level, until the
# `2026-10-21-blocs-sections` migration ran.
BLOCS_CONTAINER_PATHS = (
    "",
    "blocs.",
    "blocs.cells.blocs.",
    "blocs.items.content.",
    "blocs.items.content.cells.blocs.",
    "items.content.",
)

SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")


def _blocs_reference_fields(document_type) -> tuple[set, set]:
    """Names of the bloc fields referencing `document_type`: single references, and
    lists of references (the legacy `*ListBloc`)."""
    single, many = set(), set()
    for bloc_class in classes_by_parents.get(Bloc, set()):
        for name, mongo_field in bloc_class._fields.items():
            if isinstance(mongo_field, ReferenceField):
                if mongo_field.document_type is document_type:
                    single.add(name)
            elif isinstance(mongo_field, ListField) and isinstance(
                mongo_field.field, ReferenceField
            ):
                if mongo_field.field.document_type is document_type:
                    many.add(name)
    return single, many


def _without_reference(items: list, obj_id, single: set, many: set) -> list:
    kept = []
    for item in items:
        if any(item.get(name) == obj_id for name in single):
            continue
        emptied = False
        for key, value in item.items():
            if not isinstance(value, list) or not value:
                continue
            if key in many:
                # A legacy list keeps its bloc even once empty, as it always did.
                item[key] = [ref for ref in value if ref != obj_id]
            elif isinstance(value[0], dict):
                item[key] = _without_reference(value, obj_id, single, many)
                emptied = emptied or not item[key]
        # A container (grid, cell, section, accordion item) left empty by the purge only
        # held the removed object: it goes with it.
        if not emptied:
            kept.append(item)
    return kept


def purge_blocs_references(obj):
    """Remove the blocs (or legacy list entries) referencing a deleted object from all
    the blocs fields of Post, Site and Organization."""
    from udata.core.organization.models import Organization
    from udata.core.post.models import Post
    from udata.core.site.models import Site

    single, many = _blocs_reference_fields(type(obj))

    def purge(collection, blocs_field):
        query = {
            "$or": [
                {f"{blocs_field}.{path}{name}": obj.id}
                for path in BLOCS_CONTAINER_PATHS
                for name in single | many
            ]
        }
        for doc in collection.find(query, {blocs_field: 1}):
            blocs = _without_reference(doc[blocs_field], obj.id, single, many)
            collection.update_one({"_id": doc["_id"]}, {"$set": {blocs_field: blocs}})

    purge(Post._get_collection(), "blocs")
    purge(Organization._get_collection(), "presentation_blocs")
    for blocs_field in SITE_BLOCS_FIELDS:
        purge(Site._get_collection(), blocs_field)
