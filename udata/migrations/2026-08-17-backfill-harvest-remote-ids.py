"""
The CKAN backend used to adopt the remote resource id as `Resource.id`. It now correlates on
`harvest.remote_id`, so the resources harvested before the change need that field: their id *is*
their remote id.

`harvest.backend` comes first, because the backfill selects on it and it is missing wherever a
source stopped running (see `backfill_backends`). And `2026-08-18-deduplicate-resource-ids` comes
after both: reassigning ids first would lose the remote ids this backfill reads.
"""

import logging

from udata.harvest.backends import get_all_backends

log = logging.getLogger(__name__)

# `HarvestDatasetMetadata.backend` holds the backend display name.
CKAN_BACKENDS = ("CKAN", "DKAN")


def migrate(db):
    backfill_backends(db)
    backfill_remote_ids(db)


def backfill_backends(db):
    """Give every harvested dataset the backend of its source

    `harvest.backend` is only ever written by a harvest run, and the migration that created
    `harvest` from the extras predates the field by a month, so it could not fill it. Datasets
    whose source has since stopped running kept an empty one, which silently narrows every
    query selecting on it (`backfill_remote_ids` below included). The source knows.
    """
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
        if result.modified_count:
            log.info(f"{result.modified_count} datasets given the {backend.display_name} backend.")


def backfill_remote_ids(db):
    filled = 0
    left = 0
    for dataset in db.dataset.find({"harvest.backend": {"$in": CKAN_BACKENDS}}, {"resources": 1}):
        updates = {}
        for index, resource in enumerate(dataset["resources"]):
            harvest = resource.get("harvest")
            if not isinstance(harvest, dict):
                # Only enrich harvest metadata that already exist. A resource without any was
                # either added by hand, or harvested before udata stored them and its other
                # harvest fields are lost for good: a block holding nothing but a remote id
                # would claim a harvest that never happened. The backend recognizes those
                # resources by their id.
                left += 1
            elif "remote_id" not in harvest:
                # A rerun must not overwrite the id the deduplication reassigned.
                updates[f"resources.{index}.harvest.remote_id"] = resource["_id"]

        if updates:
            db.dataset.update_one({"_id": dataset["_id"]}, {"$set": updates})
            filled += len(updates)

    log.info(f"{filled} resources given their remote id.")
    log.info(f"{left} resources left without one, the backend matches those by id.")
