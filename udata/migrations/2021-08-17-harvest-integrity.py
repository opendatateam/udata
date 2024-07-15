"""
Remove Harvest db integrity problems
⚠️ long migration
"""

import logging

import mongoengine

from udata.core.jobs.models import PeriodicTask
from udata.harvest.models import HarvestJob, HarvestSource

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing HarvestJob source references.")

    harvest_jobs = HarvestJob.objects().no_cache().all()
    count = 0
    for harvest_job in harvest_jobs:
        try:
            harvest_job.source.id
        except mongoengine.errors.DoesNotExist:
            count += 1
            harvest_job.delete()

    log.info(f"Completed, removed {count} HarvestJob objects")

    log.info("Processing HarvestJob items references.")

    harvest_jobs = HarvestJob.objects.filter(items__0__exists=True).no_cache().all()
    count = 0
    for harvest_job in harvest_jobs:
        for item in harvest_job.items:
            try:
                item.dataset and item.dataset.id
            except mongoengine.errors.DoesNotExist:
                count += 1
                item.dataset = None
                harvest_job.save()

    log.info(f"Completed, modified {count} HarvestJob objects")

    log.info("Processing PeriodicTask objects.")

    harvest_schedules = PeriodicTask.objects.filter(
        name__startswith="Harvest", description="Periodic Harvesting"
    )
    hs = HarvestSource.objects.filter(periodic_task__in=harvest_schedules)
    unlegit_schedules = harvest_schedules.filter(id__nin=[h.periodic_task.id for h in hs])
    count = unlegit_schedules.delete()

    log.info(f"Completed, removed {count} PeriodicTask objects")
