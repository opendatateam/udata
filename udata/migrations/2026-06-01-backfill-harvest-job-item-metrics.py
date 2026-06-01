"""
Backfill the stored item counters (`items_total`, `items_by_status`,
`items_by_type`) on existing harvest jobs.

These counters are now recomputed on every save and read by the `items` link so
that listing/reading jobs no longer loads or dereferences the embedded items.
Existing jobs predate the counters, so we compute them once, server-side.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    from udata.harvest.models import HARVEST_ITEM_STATUS, HarvestJob

    collection = db[HarvestJob._get_collection_name()]
    items = {"$ifNull": ["$items", []]}

    def count_where(cond):
        return {"$size": {"$filter": {"input": items, "as": "i", "cond": cond}}}

    log.info("Backfilling harvest job item metrics.")
    result = collection.update_many(
        {},
        [
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
        ],
    )
    log.info(f"Backfilled item metrics on {result.modified_count} harvest jobs.")
