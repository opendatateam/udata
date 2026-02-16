# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mongoengine.fields import StringField

from udata.models import WithMetrics, db


class FakeModel(WithMetrics, db.Document):
    name = StringField()

    def __unicode__(self):
        return self.name or ""
