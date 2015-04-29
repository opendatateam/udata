# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g
from werkzeug.local import LocalProxy

from udata.i18n import lazy_gettext as _, gettext
from udata.models import db


__all__ = ('GeoLevel', 'GeoZone', 'SpatialCoverage', 'BASE_GRANULARITIES', 'spatial_granularities')


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


def get_spatial_granularities():
    if getattr(g, 'spatial_granularities', None) is None:
        g.spatial_granularities = [(l.id, l.name) for l in GeoLevel.objects] + BASE_GRANULARITIES
    return g.spatial_granularities


spatial_granularities = LocalProxy(get_spatial_granularities)


class SpatialCoverage(db.EmbeddedDocument):
    '''Represent a spatial coverage as a list of territories and/or a geometry'''
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
