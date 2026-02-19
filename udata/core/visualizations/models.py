from blinker import Signal
from mongoengine import EmbeddedDocument

from udata.api_fields import field
from udata.core.activity.models import Auditable
from udata.core.linkable import Linkable
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned
from udata.i18n import lazy_gettext as _
from udata.models import db


class Filter(db.Document):
    column = db.StringField(required=True)
    condition = db.StringField(required=True, choices=list(["equal", "greater"]))
    value = db.StringField()


class GenericFilter(EmbeddedDocument):
    pass


class AndFilters(GenericFilter, db.Document):
    generic_filters = db.Listfield(db.EmbeddedDocument(Filter))


class Visualization(db.Datetimed, Auditable, WithMetrics, Linkable, Owned, db.Document):
    title = field(
        db.StringField(required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        db.SlugField(
            max_length=255, required=True, populate_from="title", update=True, follow=True
        ),
        readonly=True,
        auditable=False,
    )
    description = field(
        db.StringField(required=True),
        markdown=True,
    )

    private = field(db.BooleanField(default=False), filterable={})

    extras = field(db.ExtrasField(), auditable=False)

    deleted_at = field(
        db.DateTimeField(),
        auditable=False,
    )

    def __str__(self):
        return self.title or ""

    __metrics_keys__ = [
        "views",
    ]

    meta = {
        "indexes": [
            "$title",
            "created_at",
            "last_modified",
        ]
        + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "auto_create_index_on_save": True,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()

    verbose_name = _("visualization")

    def validate(self):
        # validate des trucs
        pass

    def sources(self):
        return "toutes_les_ressources_from_yaxis"


class YAxis(
    EmbeddedDocument
):  # Maybe rename to datapoints? We may want only one YAxis configuration (min, max, layout), but multiple data points plotted
    type: list[str] = db.StringField(choices=["line", "histogram"])
    column_y = db.StringField(
        required=False
    )  # if not column y, we count the number of x. Could it ne non int/float values?
    aggregate_y = db.StringField(choices=["sum", "median"], required=False)
    resource = db.ReferenceField()
    column_x_name_override = (
        db.StringField()
    )  # if the column x name in this resource does not match the one from XAxis

    filters = db.EmbeddedDocument(GenericFilter)


class XAxis(EmbeddedDocument):
    column_x = db.StringField(required=True)
    sort_x_by = db.StringField(choices=["axis_x", "axis_y"], default="axis_x")
    sort_x_direction = db.StringField(choices=["asc", "desc"], default="asc")
    type = db.StringField(
        choices=["discrete", "continuous"], required=True
    )  # can be deduced based on the column type, but an int could actually be discrete (code postal)


class Chart(Visualization):
    x_axis = db.EmbeddedDocument(XAxis)
    y_axis = db.ListField(YAxis)


class Map(Visualization):
    pass
