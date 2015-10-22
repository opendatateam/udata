# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Discussion',)


class DiscussionQuerySet(db.BaseQuerySet):
    def from_organizations(self, user, *organizations):
        from udata.models import Dataset, Reuse  # Circular imports.
        Qs = db.Q()
        for dataset in Dataset.objects(owner=user).visible():
            Qs |= db.Q(subject=dataset)
        for org in organizations:
            for dataset in Dataset.objects(organization=org).visible():
                Qs |= db.Q(subject=dataset)
        for reuse in Reuse.objects.owned_by(*[user.id] + list(organizations)):
            Qs |= db.Q(subject=reuse)
        return self(Qs)


class Message(db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.now, required=True)
    posted_by = db.ReferenceField('User')


class Discussion(db.Document):
    user = db.ReferenceField('User')
    subject = db.ReferenceField(db.DomainModel)
    title = db.StringField(required=True)
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
        'ordering': ['created'],
        'queryset_class': DiscussionQuerySet,
    }

    def person_involved(self, person):
        """Return True if the given person has been involved in the

        discussion, False otherwise.
        """
        return any(message.posted_by == person for message in self.discussion)
