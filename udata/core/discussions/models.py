# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db

log = logging.getLogger(__name__)


class Message(db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.now, required=True)
    posted_by = db.ReferenceField('User')


class Discussion(db.Document):
    user = db.ReferenceField('User')
    subject = db.GenericReferenceField()
    title = db.StringField(required=True)
    discussion = db.ListField(db.EmbeddedDocumentField(Message))
    created = db.DateTimeField(default=datetime.now, required=True)
    closed = db.DateTimeField()
    closed_by = db.ReferenceField('User')
    extras = db.ExtrasField()

    meta = {
        'indexes': [
            'user',
            'subject',
            '-created'
        ],
        'ordering': ['-created'],
    }

    def person_involved(self, person):
        """Return True if the given person has been involved in the

        discussion, False otherwise.
        """
        return any(message.posted_by == person for message in self.discussion)

    @property
    def external_url(self):
        return self.subject.url_for(
            _anchor='discussion-{id}'.format(id=self.id),
            _external=True)
