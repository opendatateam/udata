# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Badge', 'BadgeMixin')


class BadgeMixin(object):

    def add_badge(self, badge):
        '''Perform an atomic prepend for a new badge'''
        self.update(__raw__={
            '$push': {
                'badges': {
                    '$each': [badge.to_mongo()],
                    '$position': 0
                }
            }
        })
        self.reload()

    def remove_badge(self, badge):
        '''Perform an atomic removal for a given badge'''
        self.update(__raw__={
            '$pull': {
                'badges': badge.to_mongo()
            }
        })
        self.reload()


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
