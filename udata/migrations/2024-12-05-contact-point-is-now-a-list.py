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

    # Add a `contact` role to each existing contact point.
    db.contact_point.update_many({}, {"$set": {"role": "contact"}})

    count = 0
    for collection in [db.dataset, db.dataservice]:
        for obj in collection.find({"contact_point": {"$exists": True}}):
            # Change `contact_point` to be a list of contact points.
            collection.update_one(
                {"_id": obj["_id"]}, {"$set": {"contact_point": [obj["contact_point"]]}}
            )
        # If we rename after updating the field to be a list, then we can re-run the migration.
        count += collection.update_many(
            {}, {"$rename": {"contact_point": "contact_points"}}
        ).modified_count

    log.info(f"Completed {count} objects")
