"""
This migration reduces the `schedules` documents to the fields `PeriodicTask` declares.

`PeriodicTask` used to inherit from `celerybeatmongo.models.PeriodicTask`, a
`DynamicDocument` whose scheduler wrote bookkeeping keys on every run (`run_immediately`,
`total_run_count`, `last_run_id`, …) and whose documents, allowing inheritance, carried
a `_cls` at every level. It is now a plain, strict `Document`: any undeclared key makes
MongoEngine raise `FieldDoesNotExist` on load. Keeping the declared fields rather than
removing known legacy ones covers whatever keys any instance accumulated over the years.

It also deletes the documents without a `name`: the old scheduler kept jobs in memory
between reloads and upserted their run state even after they were deleted, leaving
behind documents with no job definition at all. No `HarvestSource` can point to them,
since deleting a job already nullified the references to it.
"""

import logging

log = logging.getLogger(__name__)

FIELDS = {"_id", "name", "description", "task", "args", "kwargs", "enabled", "last_run_at"}
EMBEDDED_FIELDS = {
    "crontab": {"minute", "hour", "day_of_week", "day_of_month", "month_of_year"},
    "interval": {"every", "period"},
}


def migrate(db):
    deleted = db.schedules.delete_many({"name": {"$exists": False}}).deleted_count
    log.info(f"Deleted {deleted} PeriodicTask objects without a name")

    cleaned = 0
    for document in db.schedules.find():
        kept = {key: value for key, value in document.items() if key in FIELDS}
        for key, fields in EMBEDDED_FIELDS.items():
            if isinstance(document.get(key), dict):
                kept[key] = {k: v for k, v in document[key].items() if k in fields}
        if kept != document:
            db.schedules.replace_one({"_id": document["_id"]}, kept)
            cleaned += 1
    log.info(f"Removed undeclared keys from {cleaned} PeriodicTask objects")
