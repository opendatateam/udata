from werkzeug.local import LocalProxy

from udata.app import cache
from udata.uris import endpoint_for
from udata.i18n import _, L_, get_locale, language
from udata.models import db


__all__ = (
    'GeoLevel', 'GeoZone', 'SpatialCoverage', 'BASE_GRANULARITIES',
    'spatial_granularities',
)


BASE_GRANULARITIES = [
    ('poi', L_('POI')),
    ('other', L_('Other')),
]

ADMIN_LEVEL_MIN = 1
ADMIN_LEVEL_MAX = 110


class GeoLevel(db.Document):
    id = db.StringField(primary_key=True)
    name = db.StringField(required=True)
    admin_level = db.IntField(min_value=ADMIN_LEVEL_MIN,
                              max_value=ADMIN_LEVEL_MAX,
                              default=100)


class GeoZone(db.Document):
    id = db.StringField(primary_key=True)
    slug = db.StringField(required=True)
    name = db.StringField(required=True)
    code_insee = db.StringField(required=True)
    code_article = db.StringField(required=True)
    type = db.StringField(required=True)
    uri = db.StringField(required=True)

    meta = {
        'indexes': [
            'name'
        ]
    }

    def __str__(self):
        return self.id

    def __html__(self):
        """In use within the admin."""
        return '{name} <i>({code})</i>'.format(
            name=_(self.name), code=self.code)

    @property
    def url(self):
        return endpoint_for('territories.territory', territory=self)

    @property
    def external_url(self):
        return endpoint_for('territories.territory', territory=self, _external=True)

    def toGeoJSON(self):
        return {
            'id': self.id,
            'type': 'Feature',
            'properties': {
                'slug': self.slug,
                'name': _(self.name),
                'code_insee': self.code_insee,
                'code_article': self.code_article,
                'type': self.type,
                'uri': self.uri
            }
        }


@cache.memoize()
def get_spatial_granularities(lang):
    with language(lang):
        return [
            (l.id, _(l.name)) for l in GeoLevel.objects
        ] + [(id, label.value) for id, label in BASE_GRANULARITIES]


spatial_granularities = LocalProxy(
    lambda: get_spatial_granularities(get_locale()))


@cache.cached(timeout=50, key_prefix='admin_levels')
def get_spatial_admin_levels():
    return dict((l.id, l.admin_level) for l in GeoLevel.objects)


admin_levels = LocalProxy(get_spatial_admin_levels)


class SpatialCoverage(db.EmbeddedDocument):
    """Represent a spatial coverage as a list of territories and/or a geometry.
    """
    geom = db.MultiPolygonField()
    zones = db.ListField(db.ReferenceField(GeoZone))
    granularity = db.StringField(default='other')

    @property
    def granularity_label(self):
        return dict(spatial_granularities).get(self.granularity or 'other', 'other')

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

    @property
    def handled_zones(self):
        """Return only zones with a dedicated page."""
        return [zone for zone in self.zones if zone.handled_level]

    def clean(self):
        if 'geom' in self._get_changed_fields():
            if self.zones:
                raise db.ValidationError('The spatial coverage already has a Geozone')
        if 'zones' in self._get_changed_fields():
            if self.geom:
                raise db.ValidationError('The spatial coverage already has a Geometry')
