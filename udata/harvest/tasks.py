from udata.tasks import get_logger, job

from . import backends
from .models import HarvestSource

log = get_logger(__name__)


@job("harvest", route="low.harvest")
def harvest(self, ident):
    log.info('Launching harvest job for source "%s"', ident)

    source = HarvestSource.get(ident)
    if source.deleted or not source.active:
        log.info('Ignoring inactive or deleted source "%s"', source.id)
        return  # Ignore deleted and inactive sources
    Backend = backends.get_backend(source.backend)
    backend = Backend(source)

    backend.harvest()


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
