from flask import current_app

from udata.tasks import get_logger, job, task

from . import backends
from .models import HarvestJob, HarvestSource

log = get_logger(__name__)


@job("harvest", route="low.harvest")
def harvest(self, ident):
    log.info('Launching harvest job for source "%s"', ident)

    source = HarvestSource.get(ident)
    if source.deleted or not source.active:
        log.info('Ignoring inactive or deleted source "%s"', ident)
        return  # Ignore deleted and inactive sources
    Backend = backends.get(current_app, source.backend)
    backend = Backend(source)

    backend.harvest()


@task(ignore_result=False, route="low.harvest")
def harvest_job_item(job_id, item_id):
    log.info('Harvesting item %s for job "%s"', item_id, job_id)

    job = HarvestJob.objects.get(pk=job_id)
    Backend = backends.get(current_app, job.source.backend)
    backend = Backend(job)

    item = next(i for i in job.items if i.remote_id == item_id)

    backend.process_item(item)
    return item_id


@task(ignore_result=False, route="low.harvest")
def harvest_job_finalize(results, job_id):
    log.info('Finalize harvesting for job "%s"', job_id)
    job = HarvestJob.objects.get(pk=job_id)
    Backend = backends.get(current_app, job.source.backend)
    backend = Backend(job)
    backend.finalize()


@job("purge-harvesters", route="low.harvest")
def purge_harvest_sources(self):
    log.info("Purging HarvestSources flagged as deleted")
    from .actions import purge_sources

    purge_sources()


@job("purge-harvest-jobs", route="low.harvest")
def purge_harvest_jobs(self):
    log.info("Purging HarvestJobs older than retention policy")
    from .actions import purge_jobs

    purge_jobs()
