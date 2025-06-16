"""
Convert DublinCore-based Dataset frequencies to EU vocabulary
"""

import logging

from udata.core.dataset.constants import LEGACY_FREQUENCIES
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing datasets.")

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        if freq := LEGACY_FREQUENCIES.get(dataset.frequency):
            dataset.frequency = freq
            dataset.save()

    log.info("Completed.")
