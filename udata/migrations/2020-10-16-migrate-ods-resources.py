"""
Migrate ODS harvested resources URLS from
use_labels_for_header=true to use_labels_for_header=false
cf https://github.com/opendatateam/udata-ods/pull/169
"""

import logging

from mongoengine.errors import ValidationError

from udata.models import Dataset

log = logging.getLogger(__name__)

MIX_MATCH = ["use_labels_for_header=true", "use_labels_for_header=false"]


def migrate(db):
    log.info("Migrating ODS harvest datasets...")

    count = 0
    # datasets from ODS
    datasets = Dataset.objects.filter(**{"extras__ods:url__ne": None})
    for d in datasets:
        touched = False
        for r in d.resources:
            if r.url.endswith(MIX_MATCH[0]):
                r.url = r.url.replace(MIX_MATCH[0], MIX_MATCH[1])
                touched = True
                count += 1
        if touched:
            try:
                d.save()
            except ValidationError as e:
                log.warning(f"Error while saving dataset {d.id}: {str(e)}")

    log.info(f"Completed, {count} resources migrated.")
