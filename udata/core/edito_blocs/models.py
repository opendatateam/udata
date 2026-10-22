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
from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import get_dataset_by_resource_id
from udata.core.edito_blocs.base import Bloc, SizedMixin
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


# Legacy: the `*ListBloc` became a row of `DatasetBloc`/`ReuseBloc`/`DataserviceBloc`.
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
class DatasetBloc(SizedMixin, Bloc):
    dataset = field(
        ReferenceField("Dataset", required=True),
        nested_fields=dataset_card_fields,
    )


@generate_fields()
class ReuseBloc(SizedMixin, Bloc):
    reuse = field(
        ReferenceField("Reuse", required=True),
        nested_fields=reuse_card_fields,
    )


@generate_fields()
class DataserviceBloc(SizedMixin, Bloc):
    dataservice = field(
        ReferenceField("Dataservice", required=True),
        nested_fields=dataservice_card_fields,
    )


@generate_fields()
class TitleBloc(SizedMixin, Bloc):
    title = field(StringField(required=True))
    subtitle = field(StringField())


@generate_fields()
class LinkInBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    color = field(StringField())
    url = field(StringField())


@generate_fields()
class LinksListBloc(SizedMixin, BlocWithTitleMixin, Bloc):
    # Legacy: the paragraph is now a `MarkdownBloc` and the main link a `ButtonBloc`, see
    # `BlocWithTitleMixin`.
    paragraph = field(StringField())
    main_link_url = field(StringField())
    main_link_title = field(StringField())

    links = field(EmbeddedDocumentListField(LinkInBloc))


@generate_fields()
class ButtonBloc(SizedMixin, Bloc):
    title = field(StringField(required=True))
    url = field(StringField(required=True))


SECTION_COLORS = ("primary", "green", "purple")


# Legacy: a hero is now a colored `SectionBloc` holding a `TitleBloc` and a `ButtonBloc`,
# see `BlocWithTitleMixin`.
@generate_fields()
class HeroBloc(Bloc):
    title = field(StringField(required=True))
    description = field(StringField())
    color = field(StringField(choices=SECTION_COLORS))
    main_link_url = field(StringField())
    main_link_title = field(StringField())


@generate_fields()
class MarkdownBloc(SizedMixin, BlocWithTitleMixin, Bloc):
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
class ExploreBloc(SizedMixin, BlocWithTitleMixin, Bloc):
    resource_id = field(
        UUIDField(required=True, binary=False),
        checks=[check_resource_exists],
    )


@generate_fields()
class AccordionItemBloc(EmbeddedDocument):
    # Generated when an item without one is loaded (`AutoUUIDField`): the editor tells items
    # apart by it as they move.
    id = field(AutoUUIDField(primary_key=True))
    title = field(StringField(required=True))
    content = field(EmbeddedDocumentListField(Bloc), generic=True)


@generate_fields()
class AccordionListBloc(SizedMixin, Bloc):
    # Legacy, see `BlocWithTitleMixin`.
    title = field(StringField())
    description = field(StringField())
    items = field(EmbeddedDocumentListField(AccordionItemBloc))


@generate_fields()
class SectionBloc(Bloc):
    color = field(
        StringField(choices=SECTION_COLORS),
        description="Background of the section. Without it, the sections of a page alternate "
        "their neutral backgrounds.",
    )
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")
