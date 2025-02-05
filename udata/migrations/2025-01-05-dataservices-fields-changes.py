"""
This migration keeps only the "Local authority" badge if the organization also has the "Public service" badge.
"""

import logging

from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_TYPE_OPEN,
    DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
    DATASERVICE_ACCESS_TYPE_RESTRICTED,
)
from udata.core.dataservices.models import Dataservice

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataservices…")

    Dataservice.objects(is_restricted=True, has_token=True).update(
        access_type=DATASERVICE_ACCESS_TYPE_RESTRICTED
    )
    Dataservice.objects(is_restricted=False, has_token=True).update(
        access_type=DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT
    )
    Dataservice.objects(is_restricted=False, has_token=False).update(
        access_type=DATASERVICE_ACCESS_TYPE_OPEN
    )

    for dataservice in Dataservice.objects(is_restricted=True, has_token=False):
        print(
            f"\t Dataservice #{dataservice.id} {dataservice.title} is restricted but without token. (setting it to access_type={DATASERVICE_ACCESS_TYPE_RESTRICTED})"
        )

    Dataservice.objects(is_restricted=True, has_token=False).update(
        access_type=DATASERVICE_ACCESS_TYPE_RESTRICTED
    )

    log.info("Done")
