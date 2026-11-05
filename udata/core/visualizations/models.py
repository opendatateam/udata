from blinker import Signal
from flask.helpers import url_for
from flask_storage.mongo import ImageField
from mongoengine import EmbeddedDocument, Q
from mongoengine import ValidationError as MongoEngineValidationError
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    EmbeddedDocumentField,
    FloatField,
    StringField,
    UUIDField,
)
from mongoengine.signals import post_delete

from udata.api import api, fields
from udata.api_fields import field, generate_fields
from udata.core.auditable import Auditable
from udata.core.dataset.permissions import OwnablePermission, OwnableReadPermission
from udata.core.linkable import Linkable
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned, OwnedQuerySet
from udata.core.storages import default_image_basename, images
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.slug_fields import SlugField
from udata.sql_guard import UnsafeSQLError, assert_read_only
from udata.uris import cdata_url

from .constants import IMAGE_MAX_SIZE

visualization_permissions_fields = api.model(
    "VisualizationPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)


class ChartQuerySet(OwnedQuerySet):
    def visible(self):
        return self(deleted_at=None, private=False)

    def hidden(self):
        return self(Q(private=True) | Q(deleted_at__ne=None))


@generate_fields()
class YAxis(EmbeddedDocument):
    min = field(FloatField())
    max = field(FloatField())
    label = field(StringField())
    unit = field(StringField())
    unit_position = field(StringField(choices=["prefix", "suffix"], default="suffix"))


@generate_fields()
class Chart(Datetimed, Auditable, WithMetrics, Linkable, Owned, UDataDocument[ChartQuerySet]):
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
        readonly=True,
        auditable=False,
    )

    query = field(StringField(required=True))
    resource_id = field(UUIDField(required=True, binary=False))
    chart_type = field(StringField(choices=["line", "histogram"], default="line", required=True))
    y_axis = field(EmbeddedDocumentField(YAxis))

    def clean(self):
        super().clean()
        # Chart queries run read-only against the tabular engine; an absent
        # query is the required-field validator's job, not the guard's.
        if self.query:
            try:
                assert_read_only(self.query)
            except UnsafeSQLError as error:
                raise MongoEngineValidationError(f"Chart query is not read-only: {error}")

    image = field(
        ImageField(
            fs=images,
            basename=default_image_basename,
            max_size=IMAGE_MAX_SIZE,
        ),
        readonly=True,
        show_as_ref=True,
    )

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
        "queryset_class": ChartQuerySet,
        "auto_create_index_on_save": True,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()

    verbose_name = _("chart")

    @classmethod
    def clean_image_on_delete(cls, sender, document, **kwargs):
        """Clean up image files when a Chart is deleted"""
        from udata.core.storages import images

        if sender == Chart and document.image.filename is not None:
            storage = images
            storage.delete(document.image.filename)
            storage.delete(document.image.original)
            for key, value in document.image.thumbnails.items():
                storage.delete(value)


post_delete.connect(Chart.clean_image_on_delete, sender=Chart)
