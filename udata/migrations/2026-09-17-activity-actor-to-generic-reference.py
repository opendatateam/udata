"""
Store `Activity.actor` as a generic reference.

`actor` used to be a `ReferenceField("User")`, stored as a bare ObjectId. It is now a
`GenericReferenceField`, so that an activity can later be attributed to something else
than a user (a harvest source, an API token) and a robot be told apart from a person.
A generic reference is stored as `{"_cls": "User", "_ref": DBRef("user", <id>)}`, a
shape mongoengine cannot read a bare ObjectId as.

The whole collection is rewritten, so this runs as a single scan with batched writes
rather than one `update_many` per distinct actor: the indexes all lead with `_cls`, so
matching on `actor` alone would rescan the collection for every actor.
"""

import logging

from bson import DBRef
from mongoengine.connection import get_db
from pymongo import UpdateOne

log = logging.getLogger(__name__)

BATCH_SIZE = 1000


def migrate(db):
    activities = get_db().activity

    log.info("Converting Activity.actor to the generic reference format...")

    operations = []
    converted = 0

    def flush():
        nonlocal converted, operations
        if not operations:
            return
        activities.bulk_write(operations, ordered=False)
        converted += len(operations)
        operations = []
        log.info(f"{converted} activities converted so far...")

    cursor = activities.find(
        {"actor": {"$type": "objectId"}}, {"actor": 1}, no_cursor_timeout=True
    ).batch_size(BATCH_SIZE)
    for activity in cursor:
        operations.append(
            UpdateOne(
                {"_id": activity["_id"]},
                {"$set": {"actor": {"_cls": "User", "_ref": DBRef("user", activity["actor"])}}},
            )
        )
        if len(operations) >= BATCH_SIZE:
            flush()
    flush()

    log.info(f"Converted {converted} activities")
