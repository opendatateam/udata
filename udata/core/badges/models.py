# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Badge',)


class Badge(db.EmbeddedDocument):
    kind = db.StringField(choices=[], required=True)
    created = db.DateTimeField(default=datetime.now, required=True)
    created_by = db.ReferenceField('User')
    removed = db.DateTimeField()
    removed_by = db.ReferenceField('User')

    meta = {
        'allow_inheritance': True,
        'ordering': ['created'],
    }

    def __unicode__(self):
        return self.kind

    __str__ = __unicode__
