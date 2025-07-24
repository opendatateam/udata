from datetime import datetime

import udata.core.dataset.api_fields as datasets_api_fields
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataservices.models import Dataservice
from udata.core.owned import Owned
from udata.core.reuse.models import Reuse
from udata.i18n import lazy_gettext as _
from udata.models import db


@generate_fields()
class Bloc(db.EmbeddedDocument):
    id = field(db.AutoUUIDField(primary_key=True))
    type = field(db.StringField(required=True))

    meta = {"allow_inheritance": True}


class BlocWithTitleMixin:
    title = field(db.StringField(required=True))
    subtitle = field(db.StringField())


@generate_fields()
class DatasetsListBloc(BlocWithTitleMixin, Bloc):
    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset"),
                nested_fields=datasets_api_fields.dataset_fields,
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
class Page(Auditable, Owned, db.Document):
    blocs = field(
        db.EmbeddedDocumentListField(Bloc),
        generic={
            "datasets_list": DatasetsListBloc,
            "reuses_list": ReusesListBloc,
            "dataservices_list": DataservicesListBloc,
            "links_list": LinksListBloc,
        },
    )

    created_at = field(
        db.DateTimeField(verbose_name=_("Creation date"), default=datetime.utcnow, required=True),
        readonly=True,
        sortable="created",
        auditable=False,
    )
    updated_at = field(
        db.DateTimeField(
            verbose_name=_("Last modification date"), default=datetime.utcnow, required=True
        ),
        readonly=True,
        auditable=False,
    )
