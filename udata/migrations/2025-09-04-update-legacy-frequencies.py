"""
Convert legacy frequencies to latest vocabulary
"""

import logging

from udata.core.dataset.constants import UpdateFrequency
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Updating datasets legacy frequencies:")

    for legacy_value, frequency in UpdateFrequency._LEGACY_FREQUENCIES.items():
        count = 0
        for dataset in Dataset.objects(frequency=legacy_value).no_cache().timeout(False):
            # Explicitly call update() to force writing the new frequency string to mongo.
            # We can't rely on save() here because:
            # 1. save() only writes modified fields to mongo, basically comparing the Dataset's
            #    object state initially returned by the query with its state when save() is called,
            #    and only sending the diffset to mongo.
            # 2. At the ODM layer, the Dataset.frequency field has already been instantiated as an
            #    UpdateFrequency object, and so legacy frequency strings have already been
            #    mapped to their new ids (via UpdateFrequency._missing_).
            # => While the raw frequency string has changed, the save() function sees the same
            #    UpdateFrequency and therefore ignores the field in is diffset.
            dataset.update(frequency=frequency.value)
            # Still call save() afterwards so computed fields like quality_cached are updated if
            # necessary, e.g. if moving from a predictable timedelta to an unpredictable one.
            dataset.save()
            count += 1
        log.info(f"- {legacy_value} -> {frequency.value}: {count} updated")

    log.info("Completed.")
