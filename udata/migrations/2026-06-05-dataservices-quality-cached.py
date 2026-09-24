"""
Backfill quality_cached on all existing Dataservice documents.
"""

import logging

import click

from udata.core.dataservices.models import Dataservice

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Backfilling Dataservice.quality_cached...")

    with click.progressbar(
        Dataservice.objects(), length=Dataservice.objects().count()
    ) as dataservices:
        for dataservice in dataservices:
            try:
                dataservice.quality_cached = dataservice.compute_quality()
                dataservice.save(signal_kwargs={"ignores": ["post_save"]})
            except Exception as err:
                log.error(f"Cannot backfill quality_cached for dataservice {dataservice.id} {err}")

    log.info("Done")
