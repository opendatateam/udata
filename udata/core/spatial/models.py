import geojson
from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import IntField, ListField, MultiPolygonField, ReferenceField, StringField
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

from udata.api import fields
from udata.api_fields import field, generate_fields
from udata.app import cache
from udata.core.metrics.models import WithMetrics
from udata.i18n import _, get_locale, language
from udata.mongo.document import UDataDocument as Document
from udata.mongo.queryset import UDataQuerySet

from . import geoids
from .api_fields import geojson as geojson_fields
from .api_fields import granularity_fields
from .constants import ADMIN_LEVEL_MAX, ADMIN_LEVEL_MIN, BASE_GRANULARITIES

__all__ = ("GeoLevel", "GeoZone", "SpatialCoverage", "spatial_granularities")


class GeoLevel(Document):
    id = StringField(primary_key=True)
    name = StringField(required=True)
    admin_level = IntField(min_value=ADMIN_LEVEL_MIN, max_value=ADMIN_LEVEL_MAX, default=100)


class GeoZoneQuerySet(UDataQuerySet):
    def resolve(self, geoid, id_only=False):
        """
        Resolve a GeoZone given a GeoID.

        If `id_only` is True,
        the result will be the resolved GeoID
        instead of the resolved zone.
        """
        level, code = geoids.parse(geoid)
        qs = self(level=level, code=code)
        if id_only:
            qs = qs.only("id")
        result = qs.first()
        return result.id if id_only and result else result


@generate_fields()
class GeoZone(WithMetrics, Document[GeoZoneQuerySet]):
    SEPARATOR = ":"

    id = StringField(primary_key=True)
    slug = field(StringField(required=True), show_as_ref=True, description="The zone slug")
    name = field(StringField(required=True), show_as_ref=True, description="The zone name")
    code = field(
        StringField(required=True),
        show_as_ref=True,
        description="The zone unique code in the level",
    )
    level = field(StringField(required=True), show_as_ref=True, description="The zone level")
    uri = field(StringField(), show_as_ref=True, description="The zone uri")
    ancestors = ListField(StringField())

    meta = {
        "indexes": [
            "name",
            ("level", "code"),
        ],
        "queryset_class": GeoZoneQuerySet,
    }

    def __str__(self):
        return self.id

    def __html__(self):
        """In use within the admin."""
        return "{name} <i>({code})</i>".format(name=_(self.name), code=self.code)

    @cached_property
    def level_code(self):
        """Truncated level code for the sake of readability."""
        # Either 'region', 'departement' or 'commune',
        # useful to match TERRITORY_DATASETS keys.
        return self.id.split(":")[1]

    @cached_property
    def level_name(self):
        """Truncated level name for the sake of readability."""
        if self.level.startswith("fr:"):
            return self.level[3:]
        # Keep the whole level name as a fallback (e.g. `country:fr`)
        return self.level

    @cached_property
    def level_i18n_name(self):
        """In use within templates for dynamic translations."""
        for level, name in spatial_granularities:
            if self.level == level:
                return name
        return self.level_name  # Fallback that should never happen.

    @property
    def url(self):
        return None

    @property
    def external_url(self):
        return None

    def count_datasets(self):
        from udata.models import Dataset

        self.metrics["datasets"] = Dataset.objects(spatial__zones=self.id).visible().count()
        self.save()

    def toGeoJSON(self):
        return {
            "id": self.id,
            "type": "Feature",
            "properties": {
                "slug": self.slug,
                "name": _(self.name),
                "code": self.code,
                "uri": self.uri,
                "level": self.level,
            },
        }


@cache.memoize()
def get_spatial_granularities(lang):
    with language(lang):
        return [(geolevel.id, _(geolevel.name)) for geolevel in GeoLevel.objects] + [
            (id, str(label)) for id, label in BASE_GRANULARITIES
        ]


spatial_granularities = LocalProxy(lambda: get_spatial_granularities(get_locale()))


@cache.cached(timeout=50, key_prefix="admin_levels")
def get_spatial_admin_levels():
    return dict((geolevel.id, geolevel.admin_level) for geolevel in GeoLevel.objects)


admin_levels = LocalProxy(get_spatial_admin_levels)


@generate_fields()
class SpatialCoverage(EmbeddedDocument):
    """Represent a spatial coverage as a list of territories and/or a geometry."""

    geom = field(
        MultiPolygonField(),
        nested_fields=geojson_fields,
        allow_null=True,
        description="A multipolygon for the whole coverage",
    )
    zones = field(
        ListField(ReferenceField(GeoZone)),
        full_object=True,
        description="The covered zones identifiers (full GeoZone objects if `X-Get-Datasets-Full-Objects` is set, IDs of the zones otherwise)",
    )
    granularity = field(
        StringField(default="other"),
        default="other",
        full_object=fields.Nested(
            granularity_fields,
            attribute=lambda s: {"id": s.granularity or "other", "name": s.granularity_label},
        ),
        description="The spatial/territorial granularity (full Granularity object if `X-Get-Datasets-Full-Objects` is set, ID of the granularity otherwise)",
    )

    @property
    def granularity_label(self):
        return dict(spatial_granularities).get(self.granularity or "other", "other")

    @property
    def top_label(self):
        if not self.zones:
            return None
        top = None
        for zone in self.zones:
            if not top:
                top = zone
                continue
        return _(top.name)

    def clean(self):
        if self.zones and self.geom:
            raise ValidationError("The spatial coverage cannot contains a Geozone and a Geometry")

        if self.geom:
            try:
                geojson.loads(geojson.dumps(self.geom))
            except (ValueError, TypeError) as err:
                raise ValidationError(
                    f"Invalid GeoJSON data `{self.geom}`: {err}.", field_name="geom"
                )
