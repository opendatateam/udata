"""
The CKAN backend used to adopt the remote resource id as `Resource.id`, which udata resolves
platform-wide through the `/datasets/r/<id>` permalink. Whenever a source changed the remote id
of one of its datasets, udata created a new dataset and archived the previous one, leaving
several datasets holding resources with the same id. `get_dataset_by_resource_id` refuses to
answer for such an ambiguous id, so those permalinks return a 404.

The backend now correlates on `harvest.remote_id`, so this migration first gives that field to
the resources harvested before the change — their id *is* their remote id — then hands a fresh
id to every duplicated copy but one. The order matters: reassigning ids first would lose the
remote ids the backfill reads.

`harvest.backend` comes first, because the backfill selects on it and it is missing wherever a
source stopped running (see `backfill_backends`).
"""

import logging
from uuid import uuid4

from udata.harvest.backends import get_all_backends

log = logging.getLogger(__name__)

# `HarvestDatasetMetadata.backend` holds the backend display name.
CKAN_BACKENDS = ("CKAN", "DKAN")


def migrate(db):
    backfill_backends(db)
    backfill_remote_ids(db)
    deduplicate_resource_ids(db)


def backfill_backends(db):
    """Give every harvested dataset the backend of its source

    `harvest.backend` is only ever written by a harvest run, and the migration that created
    `harvest` from the extras predates the field by a month, so it could not fill it. Datasets
    whose source has since stopped running kept an empty one, which silently narrows every
    query selecting on it — `backfill_remote_ids` below included. The source knows.
    """
    updated = 0
    for backend in get_all_backends().values():
        source_ids = [
            str(source["_id"])
            for source in db.harvest_source.find({"backend": backend.name}, {"_id": 1})
        ]
        if not source_ids:
            continue
        result = db.dataset.update_many(
            {"harvest.source_id": {"$in": source_ids}, "harvest.backend": None},
            {"$set": {"harvest.backend": backend.display_name}},
        )
        updated += result.modified_count
    log.info(f"{updated} harvested datasets given the backend of their source.")


def backfill_remote_ids(db):
    result = db.dataset.update_many(
        {
            "harvest.backend": {"$in": CKAN_BACKENDS},
            "resources.harvest": {"$exists": True},
        },
        [
            {
                "$set": {
                    "resources": {
                        "$map": {
                            "input": "$resources",
                            "as": "resource",
                            "in": {
                                "$cond": [
                                    {
                                        "$and": [
                                            # Only enrich harvest metadata that already exist.
                                            # A resource without any was either added by hand,
                                            # or harvested before udata stored them and its
                                            # other harvest fields are lost for good: a block
                                            # holding nothing but a remote id would claim a
                                            # harvest that never happened. The backend
                                            # recognizes those resources by their id.
                                            {"$eq": [{"$type": "$$resource.harvest"}, "object"]},
                                            # A rerun must not store the id reassigned by the
                                            # deduplication below as the remote one.
                                            {
                                                "$eq": [
                                                    {"$type": "$$resource.harvest.remote_id"},
                                                    "missing",
                                                ]
                                            },
                                        ]
                                    },
                                    {
                                        "$mergeObjects": [
                                            "$$resource",
                                            {
                                                "harvest": {
                                                    "$mergeObjects": [
                                                        "$$resource.harvest",
                                                        {"remote_id": "$$resource._id"},
                                                    ]
                                                }
                                            },
                                        ]
                                    },
                                    "$$resource",
                                ]
                            },
                        }
                    }
                }
            }
        ],
    )
    log.info(f"{result.modified_count} CKAN harvested datasets given their resources remote ids.")


def deduplicate_resource_ids(db):
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
    settles it.
    """
    live = [
        dataset
        for dataset in datasets
        if dataset.get("deleted") is None and dataset.get("archived") is None
    ]
    candidates = live or [dataset for dataset in datasets if dataset.get("deleted") is None]
    candidates = candidates or datasets
    harvested = [
        dataset for dataset in candidates if (dataset.get("harvest") or {}).get("last_update")
    ]
    if harvested:
        return max(harvested, key=lambda dataset: dataset["harvest"]["last_update"])
    return max(candidates, key=lambda dataset: dataset["_id"])
