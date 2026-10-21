import copy
import logging
import uuid
from collections.abc import Callable

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

log = logging.getLogger(__name__)


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
    )


@generate_fields()
class ReuseBloc(Bloc):
    reuse = field(
        ReferenceField("Reuse", required=True),
        nested_fields=reuse_card_fields,
    )


@generate_fields()
class DataserviceBloc(Bloc):
    dataservice = field(
        ReferenceField("Dataservice", required=True),
        nested_fields=dataservice_card_fields,
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


# Where a bloc showing an object can sit inside a blocs field, following the layout checked
# by `check_blocs_layout`.
BLOCS_CONTAINER_PATHS = (
    "blocs.",
    "blocs.cells.blocs.",
    "blocs.items.content.",
    "blocs.items.content.cells.blocs.",
)

SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")

# Times the purge reads a blocs field again when an edit was saved in between.
PURGE_ATTEMPTS = 3


def blocs_reference_fields(document_type=None) -> set[str]:
    """Names of the bloc fields referencing a `document_type` (any document without it).

    The lists of references of the legacy `*ListBloc`s are left out: blocs still in that
    format are only read, and the read leaves out the objects that no longer exist.
    """
    return {
        name
        for bloc_class in classes_by_parents.get(Bloc, set())
        for name, mongo_field in bloc_class._fields.items()
        if isinstance(mongo_field, ReferenceField)
        and (document_type is None or mongo_field.document_type is document_type)
    }


def without_blocs(items: list[dict], removed: Callable[[dict], bool]) -> list[dict]:
    """Blocs as stored or serialized, without the `removed` ones, at any depth.

    A container (grid, cell, section, accordion item) left empty only held removed blocs:
    it goes with them.
    """
    kept = []
    for item in items:
        if removed(item):
            continue
        emptied = False
        for key, value in item.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                item[key] = without_blocs(value, removed)
                emptied = emptied or not item[key]
        if not emptied:
            kept.append(item)
    return kept


def purge_blocs_references(obj):
    """Remove the blocs referencing a deleted object from all the blocs fields of Post,
    Site and Organization."""
    from udata.core.organization.models import Organization
    from udata.core.post.models import Post
    from udata.core.site.models import Site

    names = blocs_reference_fields(type(obj))

    def references_obj(bloc: dict) -> bool:
        return any(bloc.get(name) == obj.id for name in names)

    def purge(collection, blocs_field):
        query = {
            "$or": [
                {f"{blocs_field}.{path}{name}": obj.id}
                for path in BLOCS_CONTAINER_PATHS
                for name in names
            ]
        }
        for doc in collection.find(query, {blocs_field: 1}):
            for _ in range(PURGE_ATTEMPTS):
                read = doc[blocs_field]
                blocs = without_blocs(copy.deepcopy(read), references_obj)
                # Written only if nobody saved the field since it was read: the whole field
                # is rewritten, an edit made in between would be lost.
                result = collection.update_one(
                    {"_id": doc["_id"], blocs_field: read}, {"$set": {blocs_field: blocs}}
                )
                if result.matched_count:
                    break
                doc = collection.find_one({"_id": doc["_id"]}, {blocs_field: 1})
                if doc is None:
                    break
            else:
                log.warning(f"Could not purge {obj!r} from {collection.name} {doc['_id']}")

    purge(Post._get_collection(), "blocs")
    purge(Organization._get_collection(), "presentation_blocs")
    for blocs_field in SITE_BLOCS_FIELDS:
        purge(Site._get_collection(), blocs_field)
