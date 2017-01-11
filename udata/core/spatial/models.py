# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app, url_for
from werkzeug.local import LocalProxy
from werkzeug import cached_property

from udata.app import cache
from udata.i18n import lazy_gettext as _, gettext, get_locale
from udata.models import db
from udata.core.storages import logos


__all__ = (
    'GeoLevel', 'GeoZone', 'SpatialCoverage', 'BASE_GRANULARITIES',
    'spatial_granularities'
)


BASE_GRANULARITIES = [
    ('poi', _('POI')),
    ('other', _('Other')),
]

ADMIN_LEVEL_MIN = 1
ADMIN_LEVEL_MAX = 110


class GeoLevel(db.Document):
    id = db.StringField(primary_key=True)
    name = db.StringField(required=True)
    admin_level = db.IntField(min_value=ADMIN_LEVEL_MIN,
                              max_value=ADMIN_LEVEL_MAX,
                              default=100)
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
        """In use within the admin."""
        return '{name} <i>({code})</i>'.format(
            name=gettext(self.name), code=self.code)

    @cached_property
    def html_title(self):
        """In use within templates."""
        if self.level_name == 'town':
            return ('{name} '
                    '<small>(<a href="{parent_url}">{parent_name}</a>)</small>'
                    '').format(name=self.name,
                               parent_url=self.parent.url,
                               parent_name=self.parent.name)
        elif self.level_name == 'county':
            return '{name} <small>({code})</small>'.format(
                name=self.name, code=self.code)
        else:
            return self.name

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

    @cached_property
    def level_i18n_name(self):
        """In use within templates for dynamic translations."""
        for level, name in spatial_granularities:
            if self.level == level:
                return name
        return self.level_name  # Fallback that should never happen.

    @cached_property
    def child_level(self):
        """Return the child level given handled levels."""
        HANDLED_LEVELS = current_app.config.get('HANDLED_LEVELS')
        try:
            return HANDLED_LEVELS[HANDLED_LEVELS.index(self.level) - 1]
        except (IndexError, ValueError):
            return None

    @cached_property
    def parent_level(self):
        """Return the parent level given handled levels."""
        HANDLED_LEVELS = current_app.config.get('HANDLED_LEVELS')
        try:
            return HANDLED_LEVELS[HANDLED_LEVELS.index(self.level) + 1]
        except (IndexError, ValueError):
            return None

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

    @property
    def parent(self):
        if self.parent_level:
            for parent in self.parents:
                if parent.startswith(self.parent_level):
                    return GeoZone.objects.get(id=parent,
                                               level=self.parent_level)

    @property
    def children(self):
        if self.child_level:
            return (GeoZone.objects(level=self.child_level,
                                    parents__in=[self.id])
                           .order_by('-population', '-area'))

    @property
    def handled_level(self):
        return self.level in current_app.config.get('HANDLED_LEVELS')

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
                'logo': self.logo_url(external=True)
            }
        }


@cache.memoize()
def get_spatial_granularities(lang):
    granularities = [(l.id, _(l.name))
                     for l in GeoLevel.objects] + BASE_GRANULARITIES
    return [(id, str(name)) for id, name in granularities]


spatial_granularities = LocalProxy(
    lambda: get_spatial_granularities(get_locale()))


@cache.cached(timeout=50)
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
        return [zone for zone in self.zones if zone.handled_level]
