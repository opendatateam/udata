"""
The purpose here is to change the contact_point reference field
to a list of reference field and rename it to contact_points
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Contact Point references.")

    db = get_db()
    count = 0
    for collection in [db.dataset, db.dataservice]:
        count += collection.update_many(
            {}, {"$rename": {"contact_point": "contact_points"}}
        ).modified_count
        for obj in collection.find({"contact_points__exists": True}):
            obj["contact_points"] = [obj["contacts_point"]]
            collection.save(obj)

    log.info(f"Completed {count} objects")
