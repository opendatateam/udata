"""
Rename Dataset.harvest.archived to Dataset.harvest.archived_at.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataset collection...")
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
