# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import WithMetrics
from udata.mongo import db


class FakeModel(WithMetrics, db.Document):
    name = db.StringField()

    def __unicode__(self):
        return self.name or ''
