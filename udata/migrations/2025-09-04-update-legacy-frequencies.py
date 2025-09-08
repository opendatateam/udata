"""
Convert legacy frequencies to latest vocabulary
"""

import logging

from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing datasets.")

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        # Mapping of legacy values occurs implicitely when dataset.frequency
        # is deserialized from mongo, so we just have to save the new value.
        # FIXME: No need to save if it didn't change.
        dataset.save()

    log.info("Completed.")
