# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery import chord
from flask import current_app

from udata.tasks import job, get_logger, task

from . import backends
from .models import HarvestSource

log = get_logger(__name__)


@job('harvest', route='low.harvest')
def harvest(self, ident):
    log.info('Launching harvest job for source "%s"', ident)

    source = HarvestSource.get(ident)
    Backend = backends.get(current_app, source.backend)
    backend = Backend(source)
    items = backend.perform_initialization()
    if items > 0:
        finalize = harvest_finalize.s(ident)
        items = [
            harvest_item.s(ident, item.remote_id) for item in backend.job.items
        ]
        chord(items)(finalize)
    elif items == 0:
        backend.finalize()


@task(ignore_result=False, route='low.harvest')
def harvest_item(source_id, item_id):
    log.info('Harvesting item %s for source "%s"', item_id, source_id)

    source = HarvestSource.get(source_id)
    job = source.get_last_job()
    Backend = backends.get(current_app, source.backend)
    backend = Backend(source, job)

    item = filter(lambda i: i.remote_id == item_id, job.items)[0]

    result = backend.process_item(item)
    return (item_id, result)


@task(ignore_result=False, route='low.harvest')
def harvest_finalize(results, source_id):
    log.info('Finalize harvesting for source "%s"', source_id)
    source = HarvestSource.get(source_id)
    job = source.get_last_job()
    Backend = backends.get(current_app, source.backend)
    backend = Backend(source, job)
    backend.finalize()


@task(route='low.harvest')
def purge_harvest_sources():
    log.info('Purging HarvestSources flagged as deleted')
    from .actions import purge_sources
    purge_sources()
