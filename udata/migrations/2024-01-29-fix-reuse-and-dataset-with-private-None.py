"""
Some old dataset/reuse don't have a `private` field. It should be False by default.
"""

import logging

from udata.models import Dataset, Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Reuse…")

    count = Reuse.objects(private=None).update(private=False)
    log.info(f"Fixed {count} Reuse objects from private None to private False.")

    log.info("Processing Datasets…")
    count = Dataset.objects(private=None).update(private=False)
    log.info(f"Fixed {count} Dataset objects from private None to private False.")

    log.info("Done")
