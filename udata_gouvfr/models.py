# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import (
    db, Dataset, User, Organization, Reuse,
)

# Dataset.extras.register('territorial_coverage', TerritorialCoverage)

Dataset.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Organization.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Reuse.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
User.extras.register('datagouv_ckan_last_sync', db.DateTimeField)

# Reuses badges
DATACONNEXIONS_5_CANDIDATE = 'dataconnexions-5-candidate'
DATACONNEXIONS_5_LAUREATE = 'dataconnexions-5-laureate'
DATACONNEXIONS_6_CANDIDATE = 'dataconnexions-6-candidate'
DATACONNEXIONS_6_LAUREATE = 'dataconnexions-6-laureate'
Reuse.__badges__.update({
    DATACONNEXIONS_5_CANDIDATE: _('Dataconnexions 5 candidate'),
    DATACONNEXIONS_5_LAUREATE: _('Dataconnexions 5 laureate'),
    DATACONNEXIONS_6_CANDIDATE: _('Dataconnexions 6 candidate'),
    DATACONNEXIONS_6_LAUREATE: _('Dataconnexions 6 laureate'),
})

# Datasets
C3 = 'c3'
Dataset.__badges__[C3] = _('C³')
