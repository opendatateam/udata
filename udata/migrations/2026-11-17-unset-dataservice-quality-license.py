"""
Remove the license criterion from the cached Dataservice metadata quality.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataservice collection...")
    db = get_db()
    result = db.dataservice.update_many(
        {"quality_cached.license": {"$exists": True}},
        {"$unset": {"quality_cached.license": ""}},
    )
    log.info(f"{result.modified_count} dataservices processed.")
