# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime

from udata.models import db
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

__all__ = ('Issue', 'Message', 'ISSUE_TYPES')


ISSUE_TYPES = {
    'tendencious': _('I want to declare a tendencious, illegal or advertising content'),
    'download': _('I have a problem downloading the data'),
    'question': _('I have a question about the data'),
    'suggestion': _('I have a suggestion about the data'),
    'other': _('Other'),
}


class Message(db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.now, required=True)
    posted_by = db.ReferenceField('User')


class Issue(db.Document):
    user = db.ReferenceField('User')
    subject = db.ReferenceField(db.DomainModel)
    title = db.StringField(required=True)
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
