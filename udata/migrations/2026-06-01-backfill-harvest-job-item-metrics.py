"""
Backfill the stored item counters (`items_total`, `items_by_status`,
`items_by_type`) on existing harvest jobs.

These counters are now recomputed on every save and read by the `items` link so
that listing/reading jobs no longer loads or dereferences the embedded items.
Existing jobs predate the counters, so we compute them once, server-side.
"""

import logging

import click

log = logging.getLogger(__name__)

# Process jobs in batches of ids so we can show progress. The counters are still
# computed server-side by the aggregation pipeline, so the (potentially huge)
# embedded items are never loaded into Python.
BATCH_SIZE = 1000


def migrate(db):
    from udata.harvest.models import HARVEST_ITEM_STATUS, HarvestJob

    collection = db[HarvestJob._get_collection_name()]
    items = {"$ifNull": ["$items", []]}

    def count_where(cond):
        return {"$size": {"$filter": {"input": items, "as": "i", "cond": cond}}}

    pipeline = [
        {
            "$set": {
                "items_total": {"$size": items},
                "items_by_type": {
                    "dataset": count_where({"$ne": [{"$ifNull": ["$$i.dataset", None]}, None]}),
                    "dataservice": count_where(
                        {"$ne": [{"$ifNull": ["$$i.dataservice", None]}, None]}
                    ),
                },
                "items_by_status": {
                    status: count_where({"$eq": ["$$i.status", status]})
                    for status in HARVEST_ITEM_STATUS
                },
            }
        },
    ]

    log.info("Backfilling harvest job item metrics.")

    ids = [doc["_id"] for doc in collection.find({}, {"_id": 1})]
    modified = 0
    with click.progressbar(length=len(ids), label="Harvest jobs") as progress:
        for start in range(0, len(ids), BATCH_SIZE):
            batch = ids[start : start + BATCH_SIZE]
            result = collection.update_many({"_id": {"$in": batch}}, pipeline)
            modified += result.modified_count
            progress.update(len(batch))

    log.info(f"Backfilled item metrics on {modified} harvest jobs.")
