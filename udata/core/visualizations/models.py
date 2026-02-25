from blinker import Signal
from flask.helpers import url_for
from mongoengine import EmbeddedDocument
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    EmbeddedDocumentField,
    FloatField,
    ListField,
    StringField,
    UUIDField,
)

from udata.api import api, fields
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataset.models import get_resource
from udata.core.dataset.permissions import OwnablePermission, OwnableReadPermission
from udata.core.linkable import Linkable
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.slug_fields import SlugField
from udata.uris import cdata_url

__all__ = (
    "Chart",
    "DataSeries",
    "XAxis",
    "YAxis",
    "Filter",
    "GenericFilter",
    "AndFilters",
)

visualization_permissions_fields = api.model(
    "VisualizationPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)


class GenericFilter(EmbeddedDocument):
    meta = {"allow_inheritance": True}


class Filter(GenericFilter):
    column = StringField(required=True)
    condition = StringField(required=True, choices=["equal", "greater"])
    value = StringField()


class AndFilters(GenericFilter):
    filters = ListField(EmbeddedDocumentField(GenericFilter))


class DataSeries(EmbeddedDocument):
    type = StringField(choices=["line", "histogram"])
    # if not column y, we count the number of x. Could it be non int/float values?
    column_y = StringField(required=False)
    aggregate_y = StringField(choices=["sum", "median"], required=False)
    resource_id = UUIDField()
    # if the column x name in this resource does not match the one from XAxis
    column_x_name_override = StringField()

    filters = EmbeddedDocumentField(GenericFilter)

    @property
    def resource(self):
        """Resolve the resource from resource_id"""
        if self.resource_id:
            return get_resource(self.resource_id)
        return None


class XAxis(EmbeddedDocument):
    column_x = StringField(required=True)
    sort_x_by = StringField(choices=["axis_x", "axis_y"], default="axis_x")
    sort_x_direction = StringField(choices=["asc", "desc"], default="asc")
    type = StringField(
        choices=["discrete", "continuous"], required=True
    )  # can be deduced based on the column type, but an int could actually be discrete (code postal)


class YAxis(EmbeddedDocument):
    min = FloatField()
    max = FloatField()
    label = StringField()
    unit = StringField()
    unit_position = StringField(choices=["prefix", "suffix"], default="suffix")


# Chart model contains the following base fields (previously from Visualization class):
# - title: Required title field (sortable, used for display)
# - slug: Auto-generated from title (unique, used in URLs)
# - description: Required markdown description
# - private: Boolean flag for private visualizations (default: False)
# - extras: Extra metadata storage
# - deleted_at: Soft delete timestamp
# - owner/organization: From Owned mixin (one required)
# - created_at/last_modified: From Datetimed mixin
# - permissions: Edit/delete/read permissions (from OwnablePermission)
# - metrics: Views tracking (from WithMetrics)


@generate_fields()
class Chart(Datetimed, Auditable, WithMetrics, Linkable, Owned, UDataDocument):
    title = field(
        StringField(required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        SlugField(max_length=255, required=True, populate_from="title", update=True, follow=True),
        readonly=True,
        auditable=False,
    )
    description = field(
        StringField(required=True),
        markdown=True,
    )

    private = field(BooleanField(default=False), filterable={})

    extras = field(ExtrasField(), auditable=False)

    deleted_at = field(
        DateTimeField(),
        auditable=False,
    )

    # Chart-specific fields
    x_axis = EmbeddedDocumentField(XAxis)
    y_axis = EmbeddedDocumentField(YAxis)
    series = ListField(EmbeddedDocumentField(DataSeries))

    @property
    @field(
        nested_fields=visualization_permissions_fields,
    )
    def permissions(self):
        return {
            "delete": OwnablePermission(self),
            "edit": OwnablePermission(self),
            "read": OwnableReadPermission(self),
        }

    def self_web_url(self, **kwargs):
        return cdata_url(f"/visualizations/{self._link_id(**kwargs)}", **kwargs)

    def self_api_url(self, **kwargs):
        return url_for(
            "api.visualization",
            visualization=self._link_id(**kwargs),
            **self._self_api_url_kwargs(**kwargs),
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

    verbose_name = _("chart")

    def sources(self):
        return "toutes_les_ressources_from_yaxis"


# Map will be implemented later if needed
# class Map(Datetimed, Auditable, WithMetrics, Linkable, Owned, UDataDocument):
#     pass
