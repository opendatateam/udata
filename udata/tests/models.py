# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.mongo import db
from udata.models import WithMetrics


class FakeModel(WithMetrics, db.Document):
    name = db.StringField()

    def __unicode__(self):
        return self.name or ''
