from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import EmbeddedDocumentListField, ListField, ReferenceField, StringField

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.models import Reuse
from udata.mongo.uuid_fields import AutoUUIDField


@generate_fields()
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))


class BlocWithTitleMixin:
    title = field(StringField(required=True))
    subtitle = field(StringField())


DATASET_CARD_MASK = "{id,title,acronym,slug,description,page,uri,private,archived,organization,owner,last_update,quality,metrics,badges,tags}"
dataset_card_fields = api.model("Dataset (card)", dict(dataset_fields), mask=DATASET_CARD_MASK)

REUSE_CARD_MASK = "{id,title,slug,description,type,url,image,image_thumbnail,page,uri,organization,owner,metrics,badges,tags,topic,private,created_at,last_modified}"
reuse_card_fields = api.model("Reuse (card)", dict(Reuse.__read_fields__), mask=REUSE_CARD_MASK)

DATASERVICE_CARD_MASK = "{id,title,acronym,slug,description,base_api_url,format,self_api_url,self_web_url,organization,owner,metrics,badges,tags,private,created_at,metadata_modified_at}"
dataservice_card_fields = api.model(
    "Dataservice (card)", dict(Dataservice.__read_fields__), mask=DATASERVICE_CARD_MASK
)


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
class MarkdownBloc(Bloc):
    # Not using BlocWithTitleMixin because title should be optional here
    title = field(StringField())
    subtitle = field(StringField())
    content = field(
        StringField(required=True),
        markdown=True,
    )


BLOCS_DISALLOWED_IN_ACCORDION = ("AccordionListBloc", "HeroBloc")


def check_no_recursive_blocs(blocs, **kwargs):
    for bloc in blocs:
        if bloc.__class__.__name__ in BLOCS_DISALLOWED_IN_ACCORDION:
            raise ValidationError(f"{bloc.__class__.__name__} cannot be nested inside an accordion")


@generate_fields()
class AccordionItemBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    content = field(
        EmbeddedDocumentListField(Bloc),
        generic=True,
        checks=[check_no_recursive_blocs],
    )


@generate_fields()
class AccordionListBloc(Bloc):
    title = field(StringField())
    description = field(StringField())
    items = field(EmbeddedDocumentListField(AccordionItemBloc))


SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")


def purge_blocs_references(ref_field, obj_id):
    """Remove references to a deleted object from all blocs in Post and Site."""
    from udata.core.post.models import Post
    from udata.core.site.models import Site

    Post._get_collection().update_many(
        {f"blocs.{ref_field}": obj_id},
        {"$pull": {f"blocs.$[b].{ref_field}": obj_id}},
        array_filters=[{f"b.{ref_field}": obj_id}],
    )
    for blocs_field in SITE_BLOCS_FIELDS:
        Site._get_collection().update_many(
            {f"{blocs_field}.{ref_field}": obj_id},
            {"$pull": {f"{blocs_field}.$[b].{ref_field}": obj_id}},
            array_filters=[{f"b.{ref_field}": obj_id}],
        )
