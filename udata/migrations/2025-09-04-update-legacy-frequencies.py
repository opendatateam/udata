"""
Convert legacy frequencies to latest vocabulary
"""

import logging

from udata.core.dataset.constants import UpdateFrequency
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing datasets.")

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        if freq := UpdateFrequency._legacy_frequencies.get(dataset.frequency):
            dataset.frequency = freq
            dataset.save()

    log.info("Completed.")
