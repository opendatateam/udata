"""
Some old dataset/reuse don't have a `private` field. It should be False by default.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Reuse…")
    result = db.reuse.update_many({"private": None}, {"$set": {"private": False}})
    log.info(f"Fixed {result.modified_count} Reuse objects from private None to private False.")

    log.info("Processing Dataset…")
    result = db.dataset.update_many({"private": None}, {"$set": {"private": False}})
    log.info(f"Fixed {result.modified_count} Dataset objects from private None to private False.")

    log.info("Done")
