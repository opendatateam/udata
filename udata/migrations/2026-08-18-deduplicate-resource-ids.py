"""
`Resource.id` is resolved platform-wide through the `/datasets/r/<id>` permalink, but the CKAN
backend used to adopt the remote resource id, which is only unique inside its portal. Whenever a
source changed the id of one of its packages, udata created a second dataset whose resources
carried the same ids as the first one. `get_dataset_by_resource_id` refuses to answer for such an
ambiguous id, so those permalinks return a 404.

This hands a fresh id to every duplicated copy but one. It runs after
`2026-08-17-backfill-harvest-remote-ids`, which gives the renumbered copies the remote id their
next harvest will recognize them by.
"""

import logging
from datetime import datetime
from uuid import uuid4

log = logging.getLogger(__name__)


def migrate(db):
    duplicates = list(
        db.dataset.aggregate(
            [
                {"$match": {"resources.0": {"$exists": True}}},
                {"$unwind": "$resources"},
                {"$group": {"_id": "$resources._id", "datasets": {"$addToSet": "$_id"}}},
                {"$match": {"$expr": {"$gt": [{"$size": "$datasets"}, 1]}}},
            ],
            allowDiskUse=True,
        )
    )
    log.info(f"{len(duplicates)} resource ids are shared by several datasets.")

    reassigned = 0
    for duplicate in duplicates:
        resource_id = duplicate["_id"]
        datasets = list(
            db.dataset.find(
                {"_id": {"$in": duplicate["datasets"]}},
                {"deleted": 1, "archived": 1, "harvest.last_update": 1},
            )
        )
        if not datasets:
            # `purge_datasets` deletes every soft-deleted dataset in one pass, and a group
            # whose copies are all deleted is one of the shapes this migration handles: it
            # can empty one between the aggregation above and this read.
            continue
        canonical = pick_canonical(datasets)
        for dataset in datasets:
            if dataset["_id"] == canonical["_id"]:
                continue
            db.dataset.update_one(
                {"_id": dataset["_id"], "resources._id": resource_id},
                {"$set": {"resources.$._id": str(uuid4())}},
            )
            reassigned += 1

    log.info(f"{reassigned} duplicated resources given a new id.")


def pick_canonical(datasets):
    """The copy that keeps the id, and therefore the permalink

    `get_dataset_by_resource_id` queries the datasets without `visible()`, so a deleted or an
    archived copy is enough to make an id ambiguous and has to be renumbered like any other.
    Deleted first, then archived, so that whatever a reader can still reach keeps the id.

    Being live is not enough to tell the current copy from a stale one: a dataset can be left
    unarchived while its harvest already flagged it `not-on-remote`. The last harvest date
    settles it, then the creation date so that a rerun picks the same one.
    """
    return max(
        datasets,
        key=lambda dataset: (
            dataset.get("deleted") is None and dataset.get("archived") is None,
            dataset.get("deleted") is None,
            (dataset.get("harvest") or {}).get("last_update") or datetime.min,
            dataset["_id"],
        ),
    )
