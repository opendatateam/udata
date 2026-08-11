"""
This migration removes the `celerybeat-mongo` fields that `PeriodicTask` no longer declares.

`PeriodicTask` used to inherit from `celerybeatmongo.models.PeriodicTask`, a
`DynamicDocument` carrying a handful of fields udata never wrote (`queue`, `expires`, …),
plus `last_run_id`, which had no reader left. It is now a plain, strict `Document`:
any leftover key would make MongoEngine raise `FieldDoesNotExist` on load.

`_cls` is deliberately kept: MongoEngine tolerates it on load and never queries on it
now that the class no longer allows inheritance.
"""

import logging

from mongoengine.connection import get_db

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
]


def migrate(db):
    result = get_db().schedules.update_many({}, {"$unset": {field: 1 for field in LEGACY_FIELDS}})
    log.info(f"Legacy PeriodicTask fields removed from {result.modified_count} objects")
