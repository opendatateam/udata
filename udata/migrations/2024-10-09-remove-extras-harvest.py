"""
Remove all dataset and resources extras["harvest"] (they will be harvested as extras["dcat"] from now on)
"""

import logging

from mongoengine.errors import ValidationError

from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Datasets.")

    datasets = (
        Dataset.objects(
            __raw__={"extras.harvest": {"$exists": True}},
        )
        .no_cache()
        .timeout(False)
    )

    datasets_count = datasets.count()
    for dataset in datasets:
        dataset.extras.pop("harvest", None)
        for resource in dataset.resources:
            resource.extras.pop("harvest", None)
        try:
            dataset.save()
        except ValidationError as e:
            log.error(f"Failed to save dataset {dataset.id}: {e}")

    log.info(f"Modified {datasets_count} datasets objects")
    log.info("Done")
