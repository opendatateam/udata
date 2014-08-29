# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db


__all__ = ('Territory', 'TerritoryReference')


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
        return TerritoryReference(name=self.name, level=self.level, code=self.code)


class TerritoryReference(db.EmbeddedDocument):
    name = db.StringField(required=True)
    level = db.StringField(required=True)
    code = db.StringField(required=True)
