"""
This migration keeps only the "Local authority" badge if the organization also has the "Public service" badge.
"""

import logging
from typing import List

from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_TYPE_OPEN,
    DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
    DATASERVICE_ACCESS_TYPE_RESTRICTED,
)
from udata.core.dataservices.models import Dataservice
from udata.mongo import db as db2

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataservices…")

    count = Dataservice.objects(db2.Q(is_restricted=None) | db2.Q(has_token=None)).update(
        access_type=DATASERVICE_ACCESS_TYPE_OPEN
    )
    print(f"{count} dataservices with one of another None")

    count = Dataservice.objects(is_restricted=True, has_token=True).update(
        access_type=DATASERVICE_ACCESS_TYPE_RESTRICTED
    )
    print(f"{count} dataservices with restricted and token")

    count = Dataservice.objects(is_restricted=False, has_token=True).update(
        access_type=DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT
    )
    print(f"{count} dataservices not restricted but with token")

    count = Dataservice.objects(is_restricted=False, has_token=False).update(
        access_type=DATASERVICE_ACCESS_TYPE_OPEN
    )
    print(f"{count} open dataservices")

    for dataservice in Dataservice.objects(is_restricted=True, has_token=False):
        print(
            f"\t Dataservice #{dataservice.id} {dataservice.title} is restricted but without token. (setting it to access_type={DATASERVICE_ACCESS_TYPE_RESTRICTED})"
        )

    count = Dataservice.objects(is_restricted=True, has_token=False).update(
        access_type=DATASERVICE_ACCESS_TYPE_RESTRICTED
    )
    print(f"{count} weird dataservices with restricted but no token")

    dataservices: List[Dataservice] = Dataservice.objects()
    for dataservice in dataservices:
        if not dataservice.endpoint_description_url:
            continue

        if (
            dataservice.endpoint_description_url
            or dataservice.endpoint_description_url.endswith(".json")
            or dataservice.endpoint_description_url.endswith(".yaml")
            or dataservice.endpoint_description_url.endswith("?format=openapi-json")
            or "getcapabilities" in dataservice.endpoint_description_url.lower()
            or "getresourcedescription" in dataservice.endpoint_description_url.lower()
            or dataservice.endpoint_description_url.startswith(
                "https://api.insee.fr/catalogue/api-docs/carbon.super"
            )
        ):
            # print(f"[MACHINE] {dataservice.endpoint_description_url}")
            dataservice.machine_documentation_url = dataservice.endpoint_description_url
        else:
            # print(f"[ HUMAN ] {dataservice.endpoint_description_url}")
            dataservice.technical_documentation_url = dataservice.endpoint_description_url

        dataservice.save()

    log.info("Done")
