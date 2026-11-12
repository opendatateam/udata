"""
Remove the stored Dataset.geopf.push.fiche_url, now computed as `datasheet_url`.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataset collection...")
    db = get_db()
    result = db.dataset.update_many(
        {"geopf.push.fiche_url": {"$exists": True}},
        {"$unset": {"geopf.push.fiche_url": ""}},
    )
    log.info(f"{result.modified_count} datasets processed.")
