# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime

from udata.models import db
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

__all__ = ('Issue', 'Message', 'ISSUE_TYPES')


ISSUE_TYPES = {
    'illegal': _('Illegal content'),
    'tendencious': _('Tendencious content'),
    'advertisement': _('Advertising content'),
    'other': _('Other'),
}


class Message(db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.now, required=True)
    posted_by = db.ReferenceField('User')


class Issue(db.Document):
    user = db.ReferenceField('User')
    subject = db.ReferenceField(db.DomainModel)
    type = db.StringField(choices=ISSUE_TYPES.keys())

    discussion = db.ListField(db.EmbeddedDocumentField(Message))

    created = db.DateTimeField(default=datetime.now, required=True)
    closed = db.DateTimeField()
    closed_by = db.ReferenceField('User')

    meta = {
        'indexes': [
            'user',
            'subject',
            'created'
        ],
        'allow_inheritance': True,
    }

    @property
    def type_label(self):
        return ISSUE_TYPES[self.type]

    @property
    def description(self):
        return self.discussion[0].content
