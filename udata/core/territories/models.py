# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import db


__all__ = ('Territory', 'TerritoryReference', 'GeoCoverage', 'GEO_GRANULARITIES')


GEO_GRANULARITIES = {
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


class GeoCoverage(db.EmbeddedDocument):
    geom = db.MultiPolygonField()
    territories = db.ListField(db.EmbeddedDocumentField(TerritoryReference))
    granularity = db.StringField(choices=GEO_GRANULARITIES.keys())

    @property
    def granularity_label(self):
        return GEO_GRANULARITIES[self.granularity or 'other']
