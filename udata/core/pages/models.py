from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import EmbeddedDocumentListField, ListField, ReferenceField, StringField

from udata.api import api, fields
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.owned import Owned
from udata.core.reuse.models import Reuse
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.uuid_fields import AutoUUIDField

page_permissions_fields = api.model(
    "PagePermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)


@generate_fields()
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))


class BlocWithTitleMixin:
    title = field(StringField(required=True))
    subtitle = field(StringField())


@generate_fields(
    mask="*,datasets{id,title,uri,page,private,archived,organization,owner,last_update,quality,metrics,description}"
)
class DatasetsListBloc(BlocWithTitleMixin, Bloc):
    datasets = field(
        ListField(
            field(
                ReferenceField("Dataset"),
                nested_fields=dataset_fields,
            )
        )
    )


@generate_fields()
class ReusesListBloc(BlocWithTitleMixin, Bloc):
    reuses = field(
        ListField(
            field(
                ReferenceField("Reuse"),
                nested_fields=Reuse.__read_fields__,
            )
        )
    )


@generate_fields()
class DataservicesListBloc(BlocWithTitleMixin, Bloc):
    dataservices = field(
        ListField(
            field(
                ReferenceField("Dataservice"),
                nested_fields=Dataservice.__read_fields__,
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


@generate_fields()
class Page(Auditable, Owned, Datetimed, Document):
    blocs = field(
        EmbeddedDocumentListField(Bloc),
        generic=True,
    )

    @property
    @field(
        nested_fields=page_permissions_fields,
    )
    def permissions(self):
        from .permissions import PageEditPermission

        return {
            "delete": PageEditPermission(self),
            "edit": PageEditPermission(self),
        }
