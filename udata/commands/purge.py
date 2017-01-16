# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import manager

from udata.core.dataset.tasks import purge_datasets
from udata.core.organization.tasks import purge_organizations
from udata.core.reuse.tasks import purge_reuses

log = logging.getLogger(__name__)


@manager.command
def purge():
    '''permanently remove data flagged as deleted'''
    log.info('Purging datasets')
    purge_datasets()

    log.info('Purging reuses')
    purge_reuses()

    log.info('Purging organizations')
    purge_organizations()

    log.info('Done')
