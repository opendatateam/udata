"""
This migration renames the organization badges for coherent cases
"""

import logging

from udata.core.organization.constants import ASSOCIATION, COMPANY, LOCAL_AUTHORITY
from udata.models import Organization

log = logging.getLogger(__name__)


mapping_legacy_to_actual = {
    "Association": ASSOCIATION,
    "Company": COMPANY,
    "Local authority": LOCAL_AUTHORITY,
}


def migrate(db):
    log.info("Processing Organizations...")

    for legacy, actual in mapping_legacy_to_actual.items():
        count = Organization.objects(badges__kind=legacy).update(set__badges__S__kind=actual)
        log.info(f"Renamed badge {actual} for {count} Organization objects.")

    log.info("Done")
