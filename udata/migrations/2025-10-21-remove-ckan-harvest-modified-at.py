"""
This migration empties harvest.modified_at field in the case of CKAN datasets.
Indeed, the value that was stored in this field was the *metadata* modification data
and not the *data* one, contrary to other backends.
"""

import logging

import click

from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    datasets = Dataset.objects(harvest__backend="CKAN", harvest__modified_at__exists=True)
    count = datasets.count()

    with click.progressbar(datasets, length=count) as datasets:
        for dataset in datasets:
            dataset.harvest.modified_at = None
            try:
                dataset.save()
            except Exception as err:
                log.error(f"Cannot save dataset {dataset.id} {err}")
    log.info(f"Updated {count} datasets")
    log.info("Done")
