# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

__all__ = ('Badge',)

PUBLIC_SERVICE = 'public-service'
CERTIFIED = 'certified'
PIVOTAL_DATA = 'pivotal-data'
BADGE_KINDS = {
    PUBLIC_SERVICE: _('Public Service'),
    CERTIFIED: _('Certified'),
    'authenticated-organization': _('Authenticated organization'),
    'dataconnexions-laureate': _('Dataconnexions laureate'),
    'dataconnexions-candidate': _('Dataconnexions candidate'),
    PIVOTAL_DATA: _('Pivotal data'),
}


class BadgeQuerySet(db.BaseQuerySet):

    def visible(self):
        return self(removed=None)


class Badge(db.Document):
    subject = db.ReferenceField(db.DomainModel)
    kind = db.StringField(choices=BADGE_KINDS.keys(), required=True)
    created = db.DateTimeField(default=datetime.now, required=True)
    created_by = db.ReferenceField('User')
    removed = db.DateTimeField()
    removed_by = db.ReferenceField('User')

    meta = {
        'indexes': [
            'kind',
            'subject',
            'created'
        ],
        'allow_inheritance': True,
        'ordering': ['created'],
        'queryset_class': BadgeQuerySet,
    }

    def __unicode__(self):
        return self.kind

    __str__ = __unicode__

    def __html__(self):
        return unicode(BADGE_KINDS[self.kind])
