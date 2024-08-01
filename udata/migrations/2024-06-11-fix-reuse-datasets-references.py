"""
Add a default topic to all reuses in db
"""

import logging

from bson import DBRef

from udata.models import Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Reuse.")

    reuses = Reuse.objects().no_cache().timeout(False)
    count = 0
    errors = 0

    for reuse in reuses:
        datasets_ids = []
        for dataset in reuse.datasets:
            if not isinstance(dataset, DBRef):
                datasets_ids.append(dataset.id)
            else:
                errors += 1

        if len(datasets_ids) != len(reuse.datasets):
            reuse.datasets = datasets_ids
            reuse.save()
            count += 1

    log.info(f"Modified {count} Reuses objects (removed {errors} datasets)")
    log.info("Done")
