# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db


class Territory(db.Document):
    name = db.StringField()
    level = db.StringField()
    code = db.StringField(unique_with='level')
    geom = db.MultiPolygonField()
    keys = db.DictField()

    meta = {

        'indexes': [
            'name',
            ('level', 'code'),
        ]
    }
