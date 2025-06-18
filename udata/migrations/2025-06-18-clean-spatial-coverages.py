"""
This migration updates Topic.featured to False when it is None.
"""

import logging

import click

from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    datasets = Dataset.objects(spatial__geom__exists=True)
    count = Dataset.objects(spatial__geom__exists=True).count()

    with click.progressbar(datasets, length=count) as datasets:
        for dataset in datasets:
            try:
                dataset.spatial.clean()
            except Exception as err:
                log.error(f"Invalid spatial in dataset #{dataset.id} '{dataset.title}' {err}")
                dataset.spatial = None
                dataset.save()
