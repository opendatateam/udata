"""
Recompute resources extension with improved detection
"""

import logging

from udata.core.storages.utils import extension
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Datasets.")

    datasets = Dataset.objects().no_cache().timeout(False)
    count = 0
    for dataset in datasets:
        save_dataset = False
        for resource in [res for res in dataset.resources if res.fs_filename]:
            detected_format = extension(resource.fs_filename)
            if detected_format != resource.format:
                save_dataset = True
                resource.format = detected_format
                count += 1
        if save_dataset:
            dataset.save(signal_kwargs={"ignores": ["post_save"]})

    log.info(f"Modified {count} resource objects")
    log.info("Done")
