# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.local import LocalProxy

from udata.app import cache
from udata.i18n import lazy_gettext as _, gettext, get_locale
from udata.models import db


__all__ = (
    'GeoLevel', 'GeoZone', 'SpatialCoverage', 'BASE_GRANULARITIES',
    'spatial_granularities'
)


BASE_GRANULARITIES = [
    ('poi', _('POI')),
    ('other', _('Other')),
]


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
        return gettext(self.name) + ' <i>(' + self.code + ')</i>'

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

    def toGeoJSON(self):
        return {
            'id': self.id,
            'type': 'Feature',
            'geometry': self.geom,
            'properties': {
                'name': self.name,
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
    granularities = [(l.id, l.name)
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
        return top.name
