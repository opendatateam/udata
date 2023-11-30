from flask import current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

from udata.app import cache
from udata.uris import endpoint_for
from udata.i18n import _, L_, get_locale, language
from udata.models import db

from . import geoids


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


class GeoZoneQuerySet(db.BaseQuerySet):

    def resolve(self, geoid, id_only=False):
        '''
        Resolve a GeoZone given a GeoID.

        If `id_only` is True,
        the result will be the resolved GeoID
        instead of the resolved zone.
        '''
        level, code = geoids.parse(geoid)
        qs = self(level=level, code=code)
        if id_only:
            qs = qs.only('id')
        result = qs.first()
        return result.id if id_only and result else result


class GeoZone(db.Document):
    SEPARATOR = ':'

    id = db.StringField(primary_key=True)
    slug = db.StringField(required=True)
    name = db.StringField(required=True)
    code = db.StringField(required=True)
    level = db.StringField(required=True)
    uri = db.StringField()

    meta = {
        'indexes': [
            'name',
            ('level', 'code'),
        ],
        'queryset_class': GeoZoneQuerySet
    }

    def __str__(self):
        return self.id

    def __html__(self):
        """In use within the admin."""
        return '{name} <i>({code})</i>'.format(
            name=_(self.name), code=self.code)

    @cached_property
    def level_code(self):
        """Truncated level code for the sake of readability."""
        # Either 'region', 'departement' or 'commune',
        # useful to match TERRITORY_DATASETS keys.
        return self.id.split(':')[1]

    @cached_property
    def level_name(self):
        """Truncated level name for the sake of readability."""
        if self.level.startswith('fr:'):
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
    def handled_level(self):
        return self.level in current_app.config.get('HANDLED_LEVELS')

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
                'code': self.code,
                'uri': self.uri,
                'level': self.level,
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
