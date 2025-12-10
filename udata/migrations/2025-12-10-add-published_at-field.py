"""
Migration: Add published_at field and populate from private field history.

Phase 1 (fast): Bulk update all public datasets with created_at_internal
Phase 2 (slow): Refine dates using activity history for more accuracy
"""

import logging

import click

from udata.core.dataset.activities import UserUpdatedDataset
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Phase 1: Bulk update with created_at_internal...")

    # Avoid downtime: set a default value immediately so the system stays functional
    result = db.dataset.update_many(
        {"private": False, "published_at": {"$exists": False}},
        [{"$set": {"published_at": "$created_at_internal"}}],
    )
    log.info(f"Phase 1 done: {result.modified_count} datasets updated")

    log.info("Phase 2: Refining dates from activity history...")

    datasets = Dataset.objects(published_at__ne=None).only("id", "created_at_internal")
    count = datasets.count()
    updated = 0

    with click.progressbar(
        datasets.no_cache().timeout(False), length=count, label="Refining dates"
    ) as progress:
        for dataset in progress:
            activity = (
                UserUpdatedDataset.objects(related_to=dataset.id, changes="private")
                .order_by("-created_at")
                .only("created_at")
                .first()
            )

            if activity and activity.created_at != dataset.created_at_internal:
                Dataset.objects(id=dataset.id).update_one(set__published_at=activity.created_at)
                updated += 1

    log.info(f"Phase 2 done: {updated} datasets refined with activity date")
