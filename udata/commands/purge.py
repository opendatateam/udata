# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import click

from udata.commands import cli, success

from udata.core.dataset.tasks import purge_datasets
from udata.core.organization.tasks import purge_organizations
from udata.core.reuse.tasks import purge_reuses

log = logging.getLogger(__name__)


@cli.command()
@click.option('-d', '--datasets', is_flag=True)
@click.option('-r', '--reuses', is_flag=True)
@click.option('-o', '--organizations', is_flag=True)
def purge(datasets, reuses, organizations):
    '''
    Permanently remove data flagged as deleted.

    If no model flag is given, all models are purged.
    '''
    purge_all = not any((datasets, reuses, organizations))

    if purge_all or datasets:
        log.info('Purging datasets')
        purge_datasets()

    if purge_all or reuses:
        log.info('Purging reuses')
        purge_reuses()

    if purge_all or organizations:
        log.info('Purging organizations')
        purge_organizations()

    success('Done')
