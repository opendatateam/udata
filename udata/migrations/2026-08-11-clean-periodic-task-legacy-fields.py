"""
This migration removes the `celerybeat-mongo` keys that `PeriodicTask` no longer declares.

`PeriodicTask` used to inherit from `celerybeatmongo.models.PeriodicTask`, a
`DynamicDocument` carrying a handful of fields udata never wrote (`queue`, `expires`, …),
plus `last_run_id`, which had no reader left. It is now a plain, strict `Document`:
any leftover key would make MongoEngine raise `FieldDoesNotExist` on load.

The embedded `_cls` keys matter for a different reason: the beat no longer goes through
MongoEngine, it reads the collection in raw pymongo and calls `crontab(**doc["crontab"])`
(`celery_mongobeat/beat.py:175`). An extra `_cls` key there raises a `TypeError` that
`reload_schedule` swallows, silently dropping the job from the schedule.

The top-level `_cls` is deliberately kept: MongoEngine tolerates it on load and never
queries on it now that the class no longer allows inheritance, and the beat ignores it.
"""

import logging

log = logging.getLogger(__name__)

LEGACY_FIELDS = [
    # Written by nobody: udata routes its tasks through `udata.tasks.router`.
    "queue",
    "exchange",
    "routing_key",
    "soft_time_limit",
    "expires",
    # `celerybeat-mongo` features udata never enabled.
    "start_after",
    "max_run_count",
    "date_changed",
    # Written by the old scheduler, read by an admin frontend removed years ago.
    "last_run_id",
    # `Interval` and `Crontab` allowed inheritance, so MongoEngine stored a `_cls` inside
    # each of them. The beat splats the crontab into `celery.schedules.crontab()`, which
    # rejects the unknown keyword.
    "crontab._cls",
    "interval._cls",
]


def migrate(db):
    result = db.schedules.update_many({}, {"$unset": {field: 1 for field in LEGACY_FIELDS}})
    log.info(f"Legacy PeriodicTask keys removed from {result.modified_count} objects")
