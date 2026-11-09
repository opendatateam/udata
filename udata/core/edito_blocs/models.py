import uuid

from mongoengine import EmbeddedDocument
from mongoengine.fields import (
    EmbeddedDocumentListField,
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

DATASET_CARD_MASK = "{id,title,acronym,slug,description,page,uri,private,archived,organization,owner,last_update,quality,metrics,badges,tags}"
dataset_card_fields = api.model("Dataset (card)", dict(dataset_fields), mask=DATASET_CARD_MASK)

REUSE_CARD_MASK = "{id,title,slug,description,type,url,image,image_thumbnail,page,uri,organization,owner,metrics,badges,tags,topic,private,created_at,last_modified}"
reuse_card_fields = api.model("Reuse (card)", dict(Reuse.__read_fields__), mask=REUSE_CARD_MASK)

DATASERVICE_CARD_MASK = "{id,title,acronym,slug,description,base_api_url,format,self_api_url,self_web_url,organization,owner,quality,metrics,badges,tags,private,created_at,metadata_modified_at}"
dataservice_card_fields = api.model(
    "Dataservice (card)", dict(Dataservice.__read_fields__), mask=DATASERVICE_CARD_MASK
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
class LinksListBloc(SizedMixin, Bloc):
    links = field(EmbeddedDocumentListField(LinkInBloc))


@generate_fields()
class ButtonBloc(SizedMixin, Bloc):
    title = field(StringField(required=True))
    url = field(StringField(required=True))


@generate_fields()
class ImageBloc(SizedMixin, Bloc):
    image = field(
        StringField(required=True),
        description="URL of the image, as returned by the upload of content images",
    )
    alt = field(
        StringField(),
        description="Text replacing the image for those who cannot see it. Without it, the "
        "image is decorative.",
    )


@generate_fields()
class CardBloc(SizedMixin, Bloc):
    """A link to a page, shown as a card: the summary pages list their subpages with them."""

    title = field(StringField(required=True))
    url = field(StringField(required=True))
    description = field(StringField())
    image = field(
        StringField(),
        description="URL of the image, as returned by the upload of content images",
    )


SECTION_COLORS = ("primary", "green", "purple")


@generate_fields()
class MarkdownBloc(SizedMixin, Bloc):
    content = field(
        StringField(required=True),
        markdown=True,
    )


def check_resource_exists(resource_id, field, **_kwargs):
    try:
        resource_id = uuid.UUID(str(resource_id))
    except ValueError:
        raise FieldValidationError(field=field, message=f"'{resource_id}' is not a valid UUID")
    if not get_dataset_by_resource_id(resource_id, exclude_resources=True):
        raise FieldValidationError(field=field, message=f"Unknown resource '{resource_id}'")


@generate_fields()
class ExploreBloc(SizedMixin, Bloc):
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
    items = field(EmbeddedDocumentListField(AccordionItemBloc))


@generate_fields()
class SectionBloc(Bloc):
    color = field(
        StringField(choices=SECTION_COLORS),
        description="Background of the section. Without it, the sections of a page alternate "
        "their neutral backgrounds.",
    )
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


@generate_fields()
class ColumnBloc(SizedMixin, Bloc):
    """Blocs stacked in a share of a row, beside the others: a title and its text beside an
    illustration."""

    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)


SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")
