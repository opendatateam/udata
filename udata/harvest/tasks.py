# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from celery import chord
from flask import current_app

from udata.tasks import job, get_logger, task

from . import backends
from .models import HarvestSource, HarvestJob

log = get_logger(__name__)


@job('harvest', route='low.harvest')
def harvest(self, ident):
    log.info('Launching harvest job for source "%s"', ident)

    source = HarvestSource.get(ident)
    Backend = backends.get(current_app, source.backend)
    backend = Backend(source)
    items = backend.perform_initialization()
    if items > 0:
        finalize = harvest_job_finalize.s(backend.job.id)
        items = [
            harvest_job_item.s(backend.job.id, item.remote_id)
            for item in backend.job.items
        ]
        chord(items)(finalize)
    elif items == 0:
        backend.finalize()


@task(ignore_result=False, route='low.harvest')
def harvest_job_item(job_id, item_id):
    log.info('Harvesting item %s for job "%s"', item_id, job_id)

    job = HarvestJob.objects.get(pk=job_id)
    Backend = backends.get(current_app, job.source.backend)
    backend = Backend(job)

    item = filter(lambda i: i.remote_id == item_id, job.items)[0]

    result = backend.process_item(item)
    return (item_id, result)


@task(ignore_result=False, route='low.harvest')
def harvest_item(source_id, item_id):
    log.info('Harvesting item %s for source "%s"', item_id, source_id)
    msg = 'harvest_item is deprecated and only here for backward comaptibility'
    warnings.warn(msg, DeprecationWarning)
    job = HarvestSource.get(source_id).get_last_job()
    return harvest_job_item(job.id, item_id)


@task(ignore_result=False, route='low.harvest')
def harvest_job_finalize(results, job_id):
    log.info('Finalize harvesting for job "%s"', job_id)
    job = HarvestJob.objects.get(pk=job_id)
    Backend = backends.get(current_app, job.source.backend)
    backend = Backend(job)
    backend.finalize()


@task(ignore_result=False, route='low.harvest')
def harvest_finalize(results, source_id):
    log.info('Finalize harvesting for source "%s"', source_id)
    msg = 'harvest_item is deprecated and only here for backward comaptibility'
    warnings.warn(msg, DeprecationWarning)
    source = HarvestSource.get(source_id)
    job = source.get_last_job()
    harvest_job_finalize(results, job.id)


@task(route='low.harvest')
def purge_harvest_sources():
    log.info('Purging HarvestSources flagged as deleted')
    from .actions import purge_sources
    purge_sources()
