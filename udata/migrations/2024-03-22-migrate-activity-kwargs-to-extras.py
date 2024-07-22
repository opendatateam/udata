"""
Migrates `Activity.kwargs` to `Activity.extras`.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing activity objects")

    result = get_db().activity.update_many(filter={}, update={"$rename": {"kwargs": "extras"}})

    log.info(f"{result.modified_count} activity object(s) migrated")
    log.info("Done")
