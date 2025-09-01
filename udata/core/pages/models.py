from udata.api import api, fields
from udata.api_fields import field, function_field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.owned import Owned
from udata.core.reuse.models import Reuse
from udata.models import db
from udata.mongo.datetime_fields import Datetimed

page_permissions_fields = api.model(
    "PagePermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)


@generate_fields()
class Bloc(db.EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(db.AutoUUIDField(primary_key=True))


class BlocWithTitleMixin:
    title = field(db.StringField(required=True))
    subtitle = field(db.StringField())


@generate_fields(
    mask="*,datasets{id,title,uri,page,private,archived,organization,owner,last_update,quality,metrics,description}"
)
class DatasetsListBloc(BlocWithTitleMixin, Bloc):
    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset"),
                nested_fields=dataset_fields,
            )
        )
    )


@generate_fields()
class ReusesListBloc(BlocWithTitleMixin, Bloc):
    reuses = field(
        db.ListField(
            field(
                db.ReferenceField("Reuse"),
                nested_fields=Reuse.__read_fields__,
            )
        )
    )


@generate_fields()
class DataservicesListBloc(BlocWithTitleMixin, Bloc):
    dataservices = field(
        db.ListField(
            field(
                db.ReferenceField("Dataservice"),
                nested_fields=Dataservice.__read_fields__,
            )
        )
    )


@generate_fields()
class LinkInBloc(db.EmbeddedDocument):
    title = field(db.StringField(required=True))
    color = field(db.StringField())
    url = field(db.StringField())


@generate_fields()
class LinksListBloc(BlocWithTitleMixin, Bloc):
    paragraph = field(db.StringField())
    main_link_url = field(db.StringField())
    main_link_title = field(db.StringField())

    links = field(db.EmbeddedDocumentListField(LinkInBloc))


@generate_fields()
class Page(Auditable, Owned, Datetimed, db.Document):
    blocs = field(
        db.EmbeddedDocumentListField(Bloc),
        generic=True,
    )

    @property
    @function_field(
        nested_fields=page_permissions_fields,
    )
    def permissions(self):
        from .permissions import PageEditPermission

        return {
            "delete": PageEditPermission(self),
            "edit": PageEditPermission(self),
        }
