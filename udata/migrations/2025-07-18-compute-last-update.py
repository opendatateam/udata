"""
This migration computes the dataset last_udpate property that is now stored in the model.
It simply iterates on dataset and save them, triggering the clean() method where the last_update compute ocurs.
"""

import logging

import click

from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Saving all datasets")

    with click.progressbar(Dataset.objects(), length=Dataset.objects().count()) as datasets:
        for dataset in datasets:
            try:
                dataset.save()
            except Exception as err:
                log.error(f"Cannot save dataset {dataset.id} {err}")

    log.info("Done")
