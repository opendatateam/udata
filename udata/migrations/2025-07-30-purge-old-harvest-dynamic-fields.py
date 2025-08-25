"""
This migration removes legacy harvest dynamic fields
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    # Remove legacy fields (`ods_has_records`, `ods_url`, ...) from old harvested datasets and resources
    dataset_legacy_fields = ["ods_has_records", "ods_url", "ods_geo"]
    for field in dataset_legacy_fields:
        result = get_db().dataset.update_many({}, {"$unset": {f"harvest.{field}": 1}})
        log.info(
            f"Harvest Dataset dynamic legacy fields ({field}) removed from {result.modified_count} objects"
        )

    resource_legacy_fields = ["ods_type"]
    for field in resource_legacy_fields:
        result = get_db().dataset.update_many(
            {"resources": {"$exists": True, "$type": "array"}},
            {"$unset": {f"resources.$[].harvest.{field}": 1}},
        )
        log.info(
            f"Harvest Resource dynamic legacy fields ({field}) removed from {result.modified_count} objects"
        )
