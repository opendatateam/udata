# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import db

from . import LEVELS


__all__ = ('Territory', 'TerritoryReference', 'SpatialCoverage', 'SPATIAL_GRANULARITIES')


SPATIAL_GRANULARITIES = {
    'poi': _('POI'),
    'iris': _('Iris (Insee districts)'),
    'town': _('Town'),
    'canton': _('Canton'),
    'epci': _('Intermunicipal (EPCI)'),
    'county': _('County'),
    'region': _('Region'),
    'country': _('Country'),
    'other': _('Other'),
}


class Territory(db.Document):
    name = db.StringField(required=True)
    level = db.StringField(required=True)
    code = db.StringField(unique_with='level')
    geom = db.MultiPolygonField(required=True)
    keys = db.DictField()

    meta = {

        'indexes': [
            'name',
            ('level', 'code'),
        ]
    }

    def reference(self):
        return TerritoryReference(id=self.id, name=self.name, level=self.level, code=self.code)

    def __unicode__(self):
        return self.name


class TerritoryReference(db.EmbeddedDocument):
    id = db.ObjectIdField(required=True)
    name = db.StringField(required=True)
    level = db.StringField(required=True)
    code = db.StringField(required=True)

    def __unicode__(self):
        return self.name


class SpatialCoverage(db.EmbeddedDocument):
    '''Represent a spatial coverage as a list of territories and/or a geometry'''
    geom = db.MultiPolygonField()
    territories = db.ListField(db.EmbeddedDocumentField(TerritoryReference))
    granularity = db.StringField(choices=SPATIAL_GRANULARITIES.keys())

    @property
    def granularity_label(self):
        return SPATIAL_GRANULARITIES[self.granularity or 'other']

    @property
    def top_label(self):
        if not self.territories:
            return None
        top = None
        for territory in self.territories:
            if not top:
                top = territory
                continue
            if LEVELS[territory.level]['position'] < LEVELS[top.level]['position']:
                top = territory
        return top.name
