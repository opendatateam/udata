# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db, WithMetrics


__all__ = ('Site', )


DEFAULT_FEED_SIZE = 20


class Site(WithMetrics, db.Document):
    id = db.StringField(primary_key=True)
    title = db.StringField(required=True)
    keywords = db.ListField(db.StringField())
    feed_size = db.IntField(required=True, default=DEFAULT_FEED_SIZE)
    configs = db.DictField()
    themes = db.MapField(db.EmbeddedDocumentField('ThemeConfig'))
