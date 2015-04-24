# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db, Dataset, User, Organization, Reuse

# TODO: service_public flag as an extension


# Dataset.extras.register('territorial_coverage', TerritorialCoverage)

Dataset.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Organization.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Reuse.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
User.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
