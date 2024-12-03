"""
This migration keeps only the "Local authority" badge if the organization also has the "Public service" badge.
"""

import logging

from mongoengine.queryset.visitor import Q

from udata.core.organization.constants import LOCAL_AUTHORITY, PUBLIC_SERVICE
from udata.models import Organization

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Organizations...")
    query = Q(badges__kind=LOCAL_AUTHORITY) & Q(badges__kind=PUBLIC_SERVICE)

    count = Organization.objects(query).update(pull__badges__kind=PUBLIC_SERVICE)
    log.info(f"Removed badge {PUBLIC_SERVICE} for {count} Organization objects.")

    log.info("Done")
