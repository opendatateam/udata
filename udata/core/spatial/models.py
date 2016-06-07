# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from werkzeug.local import LocalProxy
from werkzeug import cached_property

from udata.app import cache
from udata.i18n import lazy_gettext as _, gettext, get_locale
from udata.models import db
from udata.core.storages import logos


__all__ = (
    'GeoLevel', 'GeoZone', 'SpatialCoverage', 'BASE_GRANULARITIES',
    'spatial_granularities', 'HANDLED_ZONES'
)


BASE_GRANULARITIES = [
    ('poi', _('POI')),
    ('other', _('Other')),
]

HANDLED_ZONES = ('fr/town', 'fr/county', 'fr/region')


class GeoLevel(db.Document):
    id = db.StringField(primary_key=True)
    name = db.StringField(required=True)
    parents = db.ListField(db.ReferenceField('self'))


class GeoZone(db.Document):
    id = db.StringField(primary_key=True)
    name = db.StringField(required=True)
    level = db.StringField(required=True)
    code = db.StringField(unique_with='level')
    geom = db.MultiPolygonField(required=True)
    parents = db.ListField()
    keys = db.DictField()
    population = db.IntField()
    area = db.FloatField()
    wikipedia = db.StringField()
    dbpedia = db.StringField()
    logo = db.ImageField(fs=logos)

    meta = {
        'indexes': [
            'name',
            'parents',
            ('level', 'code'),
        ]
    }

    def __unicode__(self):
        return self.id

    __str__ = __unicode__

    def __html__(self):
        return '{name} <i>({code})</i>'.format(
            name=gettext(self.name), code=self.code)

    def logo_url(self, external=False):
        filename = self.logo.filename
        if filename and self.logo.fs.exists(filename):
            return self.logo.fs.url(filename, external=external)
        else:
            return ''

    @property
    def keys_values(self):
        """Key values might be a list or not, always return a list."""
        keys_values = []
        for value in self.keys.values():
            if isinstance(value, list):
                keys_values += value
            elif not str(value).startswith('-'):  # Avoid -99.
                keys_values.append(value)
        return keys_values

    @cached_property
    def level_name(self):
        """Truncated level name for the sake of readability."""
        if self.level.startswith('fr/'):
            return self.level[3:]
        # Keep the whole level name as a fallback (e.g. `country/fr`)
        return self.level

    @property
    def url(self):
        return url_for('territories.territory', territory=self)

    @property
    def external_url(self):
        return url_for('territories.territory', territory=self, _external=True)

    @cached_property
    def wikipedia_url(self):
        """Computed wikipedia URL from the DBpedia one."""
        return (self.dbpedia.replace('dbpedia', 'wikipedia')
                            .replace('resource', 'wiki'))

    @cached_property
    def postal_string(self):
        """Return a list of postal codes separated by commas."""
        return ', '.join(self.keys.get('postal', []))

    @cached_property
    def town_repr(self):
        """Representation of a town with optional county."""
        if self.county:
            return ('{name} '
                    '<small>(<a href="{county_url}">{county_name}</a>)</small>'
                    '').format(name=self.name,
                               county_url=self.county.url,
                               county_name=self.county.name)
        return self.name

    @cached_property
    def county_repr(self):
        """Representation of a county."""
        return '{name} <small>({code})</small>'.format(
            name=self.name, code=self.code)

    @cached_property
    def region_repr(self):
        """Representation of a region."""
        return self.name

    def get_parent(self, level):
        for parent in self.parents:
            if parent.startswith(level):
                return GeoZone.objects.get(id=parent, level=level)

    @cached_property
    def county(self):
        return self.get_parent('fr/county')

    @cached_property
    def region(self):
        return self.get_parent('fr/region')

    def get_children(self, level):
        return (GeoZone.objects(level=level, parents__in=[self.id])
                       .order_by('-population', '-area'))

    @cached_property
    def towns(self):
        return self.get_children('fr/town')

    @cached_property
    def counties(self):
        return self.get_children('fr/county')

    @cached_property
    def regions(self):
        return self.get_children('fr/region')

    @property
    def handled_zone(self):
        return self.level in HANDLED_ZONES

    def toGeoJSON(self):
        return {
            'id': self.id,
            'type': 'Feature',
            'geometry': self.geom,
            'properties': {
                'name': gettext(self.name),
                'level': self.level,
                'code': self.code,
                'parents': self.parents,
                'keys': self.keys,
                'population': self.population,
                'area': self.area,
            }
        }


@cache.memoize()
def get_spatial_granularities(lang):
    granularities = [(l.id, _(l.name))
                     for l in GeoLevel.objects] + BASE_GRANULARITIES
    return [(id, str(name)) for id, name in granularities]


spatial_granularities = LocalProxy(
    lambda: get_spatial_granularities(get_locale()))


class SpatialCoverage(db.EmbeddedDocument):
    """Represent a spatial coverage as a list of territories and/or a geometry.
    """
    geom = db.MultiPolygonField()
    zones = db.ListField(db.ReferenceField(GeoZone))
    granularity = db.StringField(default='other')

    @property
    def granularity_label(self):
        return _(dict(spatial_granularities)[self.granularity or 'other'])

    @property
    def top_label(self):
        if not self.zones:
            return None
        top = None
        for zone in self.zones:
            if not top:
                top = zone
                continue
            if zone.id in top.parents:
                top = zone
        return _(top.name)

    @property
    def handled_zones(self):
        """Return only zones with a dedicated page."""
        return [zone for zone in self.zones if zone.handled_zone]
