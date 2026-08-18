"""
TODO
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Dataset collection...")
    db = get_db()
    result = db.dataset.update_many(
        {},
        {
            "$rename": {
                "harvest.archived": "harvest.archived_reason",
            }
        },
    )
    log.info(f"{result.modified_count} datasets processed.")
