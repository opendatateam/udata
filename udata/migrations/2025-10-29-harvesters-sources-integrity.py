"""
Fix HarvestSource with removed `periodic_task`
"""

import logging

import mongoengine

from udata.harvest.models import HarvestSource

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing HarvestSource periodic_task.")

    sources = HarvestSource.objects
    count = 0
    for source in sources:
        try:
            source.schedule  # query periodic_task
        except mongoengine.errors.DoesNotExist:
            count += 1
            source.periodic_task = None
            source.save()

    log.info(f"Modified {count} sources")
