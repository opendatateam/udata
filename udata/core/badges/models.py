# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from mongoengine.signals import post_save

from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Badge', 'BadgeMixin')


class Badge(db.EmbeddedDocument):
    kind = db.StringField(choices=[], required=True)
    created = db.DateTimeField(default=datetime.now, required=True)
    created_by = db.ReferenceField('User')
    removed = db.DateTimeField()
    removed_by = db.ReferenceField('User')

    meta = {
        'ordering': ['created'],
    }

    def __unicode__(self):
        return self.kind

    __str__ = __unicode__

    def validate(self, clean=True):
        badges = getattr(self._instance, '__badges__', {})
        if self.kind not in badges.keys():
            raise db.ValidationError('Unknown badge type: %s' % self.kind)
        return super(Badge, self).validate(clean=clean)


class BadgesList(db.EmbeddedDocumentListField):
    def __init__(self, *args, **kwargs):
        return super(BadgesList, self).__init__(Badge, *args, **kwargs)

    def validate(self, value):
        print 'validate badges', value, len(value)
        return True


class BadgeMixin(object):
    badges = BadgesList()

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
        post_save.send(self.__class__, document=self)

    def remove_badge(self, badge):
        '''Perform an atomic removal for a given badge'''
        self.update(__raw__={
            '$pull': {
                'badges': badge.to_mongo()
            }
        })
        self.reload()
        post_save.send(self.__class__, document=self)
