"""
Datasets linked to an inactive harvester are archived
"""

import logging

from mongoengine.errors import ValidationError

from udata.harvest.actions import archive_harvested_dataset
from udata.harvest.models import HarvestSource
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Computing the list of datasets linked to an inactive harvester.")

    active_sources = [str(source.id) for source in HarvestSource.objects()]
    dangling_datasets = Dataset.objects(
        **{
            "extras__harvest:source_id__exists": True,
            "extras__harvest:source_id__nin": active_sources,
            "archived": None,
        }
    )

    log.info(f"{dangling_datasets.count()} datasets to archive.")

    for dataset in dangling_datasets:
        try:
            archive_harvested_dataset(dataset, reason="harvester-inactive", dryrun=False)
        except ValidationError as e:
            log.error(f"Error on dataset {dataset.id}: {e}")

    log.info("Done")
