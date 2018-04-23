# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from flask import current_app, url_for
from werkzeug.local import LocalProxy
from werkzeug import cached_property

from udata.app import cache
from udata.i18n import _, L_, get_locale, language
from udata.models import db
from udata.core.storages import logos

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
EMPTY_GEOM = {'type': 'MultiPolygon', 'coordinates': []}


class GeoLevel(db.Document):
    id = db.StringField(primary_key=True)
    name = db.StringField(required=True)
    admin_level = db.IntField(min_value=ADMIN_LEVEL_MIN,
                              max_value=ADMIN_LEVEL_MAX,
                              default=100)
    parents = db.ListField(db.ReferenceField('self'))


class GeoZoneQuerySet(db.BaseQuerySet):
    def valid_at(self, valid_date):
        '''Limit current QuerySet to zone valid at a given date'''
        is_valid = db.Q(validity__end__gt=valid_date,
                        validity__start__lte=valid_date)
        no_validity = db.Q(validity=None)
        return self(is_valid | no_validity)

    def latest(self):
        '''
        Fetch the latest valid zone matching a QuerySet.

        Ensuring the QuerySet unicity for (level, code)
        is you responsibility.
        '''
        return self.order_by('-validity__end').first()

    def resolve(self, geoid, id_only=False):
        '''
        Resolve a GeoZone given a GeoID.

        The start date is resolved from the given GeoID,
        ie. it find there is a zone valid a the geoid validity,
        resolve the `latest` alias
        or use `latest` when no validity is given.

        If `id_only` is True,
        the result will be the resolved GeoID
        instead of the resolved zone.
        '''
        level, code, validity = geoids.parse(geoid)
        qs = self(level=level, code=code)
        if id_only:
            qs = qs.only('id')
        if validity == 'latest':
            result = qs.latest()
        else:
            result = qs.valid_at(validity).first()
        return result.id if id_only and result else result


class GeoZone(db.Document):
    SEPARATOR = ':'

    id = db.StringField(primary_key=True)
    slug = db.StringField(required=True)
    name = db.StringField(required=True)
    level = db.StringField(required=True)
    code = db.StringField(required=True)
    geom = db.MultiPolygonField(null=True)
    parents = db.ListField()
    keys = db.DictField()
    validity = db.EmbeddedDocumentField(db.DateRange)
    ancestors = db.ListField()
    successors = db.ListField()
    population = db.IntField()
    area = db.FloatField()
    wikipedia = db.StringField()
    dbpedia = db.StringField()
    flag = db.ImageField(fs=logos)
    blazon = db.ImageField(fs=logos)
    logo = db.ImageField(fs=logos)

    meta = {
        'indexes': [
            'name',
            'parents',
            ('level', 'code'),
        ],
        'queryset_class': GeoZoneQuerySet
    }

    def __unicode__(self):
        return self.id

    def __html__(self):
        """In use within the admin."""
        return '{name} <i>({code})</i>'.format(
            name=_(self.name), code=self.code)

    def logo_url(self, external=False):
        flag_filename = self.flag.filename
        blazon_filename = self.blazon.filename
        if flag_filename and self.flag.fs.exists(flag_filename):
            return self.flag.fs.url(flag_filename, external=external)
        elif blazon_filename and self.blazon.fs.exists(blazon_filename):
            return self.blazon.fs.url(blazon_filename, external=external)
        else:
            return ''

    @property
    def keys_values(self):
        """Key values might be a list or not, always return a list."""
        keys_values = []
        for value in self.keys.values():
            if isinstance(value, list):
                keys_values += value
            elif isinstance(value, basestring) and not value.startswith('-'):
                # Avoid -99. Should be fixed in geozones
                keys_values.append(value)
            elif isinstance(value, int) and value >= 0:
                # Avoid -99. Should be fixed in geozones
                keys_values.append(str(value))
        return keys_values

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

    @cached_property
    def ancestors_objects(self):
        """Ancestors objects sorted by name."""
        ancestors_objects = []
        for ancestor in self.ancestors:
            try:
                ancestor_object = GeoZone.objects.get(id=ancestor)
            except GeoZone.DoesNotExist:
                continue
            ancestors_objects.append(ancestor_object)
        ancestors_objects.sort(key=lambda a: a.name)
        return ancestors_objects

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
    def parents_objects(self):
        if self.parent_level:
            for parent in self.parents:
                if parent.startswith(self.parent_level):
                    yield GeoZone.objects.get(id=parent,
                                              level=self.parent_level)

    @cached_property
    def current_parent(self):
        today = date.today()
        for parent in self.parents_objects:
            if parent.valid_at(today):
                return parent

    @property
    def children(self):
        return (GeoZone
                .objects(level=self.child_level, parents__in=[self.id])
                .order_by('name'))

    @property
    def biggest_children(self):
        return self.children.order_by('-population', '-area')[:10]

    @property
    def handled_level(self):
        return self.level in current_app.config.get('HANDLED_LEVELS')

    def valid_at(self, valid_date):
        if not self.validity:
            return True
        return self.validity.start <= valid_date <= self.validity.end

    def toGeoJSON(self):
        return {
            'id': self.id,
            'type': 'Feature',
            'geometry': self.geom or EMPTY_GEOM,
            'properties': {
                'slug': self.slug,
                'name': _(self.name),
                'level': self.level,
                'code': self.code,
                'validity': self.validity,
                'parents': self.parents,
                'keys': self.keys,
                'population': self.population,
                'area': self.area,
                'logo': self.logo_url(external=True)
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
        return dict(spatial_granularities)[self.granularity or 'other']

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
