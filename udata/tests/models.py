# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mongoengine.fields import StringField

from udata.models import WithMetrics
from udata.mongo.document import UDataDocument as Document


class FakeModel(WithMetrics, Document):
    name = StringField()

    def __unicode__(self):
        return self.name or ""
