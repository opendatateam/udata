# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db, Dataset, User, Organization, Reuse
from udata.i18n import lazy_gettext as _

# Ensure territories are registered
from . import territories  # noqa

# TODO: service_public flag as an extension
# TODO: Remove legacy territorial coverage

TERRITORIAL_GRANULARITIES = {
    'poi': _('POI'),
    'iris': _('Iris (Insee districts)'),
    'town': _('Town'),
    'canton': _('Canton'),
    'epci': _('Intermunicipal (EPCI)'),
    'county': _('County'),
    'region': _('Region'),
    'country': _('Country'),
    'other': _('Other'),
}


class TerritorialCoverage(db.EmbeddedDocument):
    codes = db.ListField(db.StringField())
    granularity = db.StringField(choices=TERRITORIAL_GRANULARITIES.keys())

    def serialize(self):
        return {
            'codes': self.codes,
            'granularity': self.granularity,
        }

Dataset.extras.register('territorial_coverage', TerritorialCoverage)

Dataset.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Organization.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Reuse.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
User.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
