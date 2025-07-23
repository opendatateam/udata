from datetime import datetime

import udata.core.dataset.api_fields as datasets_api_fields
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.owned import Owned
from udata.i18n import lazy_gettext as _
from udata.models import db


@generate_fields()
class Bloc(db.EmbeddedDocument):
    type = field(db.StringField(required=True))

    meta = {"allow_inheritance": True}


@generate_fields()
class DatasetsListBloc(Bloc):
    title = field(db.StringField(required=True))
    subtitle = field(db.StringField())

    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset"),
                nested_fields=datasets_api_fields.dataset_fields,
            )
        )
    )


@generate_fields()
class Page(Auditable, Owned, db.Document):
    blocs = field(
        db.EmbeddedDocumentListField(Bloc),
        generic={
            "datasets_list": DatasetsListBloc,
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
