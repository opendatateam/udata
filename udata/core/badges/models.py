# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

__all__ = ('Badge',)

PUBLIC_SERVICE = 'public-service'
PIVOTAL_DATA = 'pivotal-data'
BADGE_KINDS = {
    PUBLIC_SERVICE: _('Public Service'),
    'authenticated-organization': _('Authenticated organization'),
    'dataconnexions-laureate': _('Dataconnexions laureate'),
    'dataconnexions-candidate': _('Dataconnexions candidate'),
    PIVOTAL_DATA: _('Pivotal data'),
}


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
    }
