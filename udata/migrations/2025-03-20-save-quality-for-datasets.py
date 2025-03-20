"""
This migration keeps only the "Local authority" badge if the organization also has the "Public service" badge.
"""

import logging

import click

from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Saving all datasets")

    count = Dataset.objects().count()
    with click.progressbar(Dataset.objects(), length=count) as datasets:
        for dataset in datasets:
            try:
                dataset.save()
            except Exception as err:
                log.error(f"Cannot save dataset {dataset.id} {err}")

    log.info("Done")
