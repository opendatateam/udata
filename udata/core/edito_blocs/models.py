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
from udata.core.edito_blocs.base import Bloc
from udata.core.reuse.models import Reuse
from udata.mongo.errors import FieldValidationError


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


@generate_fields()
class SectionBloc(Bloc):
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")
