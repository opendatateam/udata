"""
This migration keeps only the "Local authority" badge if the organization also has the "Public service" badge.
"""

import logging
from typing import List

from mongoengine.connection import get_db

from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_TYPE_OPEN,
    DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
    DATASERVICE_ACCESS_TYPE_RESTRICTED,
)
from udata.core.dataservices.models import Dataservice

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing dataservices…")

    count = get_db().dataservice.update_many(
        filter={
            "$or": [
                {
                    "is_restricted": None,
                    "has_token": None,
                },
                {"is_restricted": {"$exists": False}},
                {"has_token": {"$exists": False}},
            ]
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_OPEN}},
    )
    print(f"{count.modified_count} dataservices with one of another None")

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": True,
            "has_token": True,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_RESTRICTED}},
    )
    print(f"{count.modified_count} dataservices with restricted and token")

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": False,
            "has_token": True,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT}},
    )
    print(f"{count.modified_count} dataservices not restricted but with token")

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": False,
            "has_token": False,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_OPEN}},
    )
    print(f"{count.modified_count} open dataservices")

    for dataservice in get_db().dataservice.find({"is_restricted": True, "has_token": False}):
        print(
            f"\t Dataservice #{dataservice['_id']} {dataservice['title']} is restricted but without token. (setting it to access_type={DATASERVICE_ACCESS_TYPE_RESTRICTED})"
        )

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": True,
            "has_token": False,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_RESTRICTED}},
    )
    print(f"{count.modified_count} weird dataservices with restricted but no token")

    dataservices: List[Dataservice] = get_db().dataservice.find()
    for dataservice in dataservices:
        if (
            "endpoint_description_url" not in dataservice
            or not dataservice["endpoint_description_url"]
        ):
            continue

        to_set = {}
        if (
            dataservice["endpoint_description_url"].endswith(".json")
            or dataservice["endpoint_description_url"].endswith(".yaml")
            or dataservice["endpoint_description_url"].endswith("?format=openapi-json")
            or "getcapabilities" in dataservice["endpoint_description_url"].lower()
            or "getresourcedescription" in dataservice["endpoint_description_url"].lower()
            or dataservice["endpoint_description_url"].startswith(
                "https://api.insee.fr/catalogue/api-docs/carbon.super"
            )
        ):
            # print(f"[MACHINE] {dataservice["endpoint_description_url"]}")
            to_set["machine_documentation_url"] = dataservice["endpoint_description_url"]
        else:
            # print(f"[ HUMAN ] {dataservice["endpoint_description_url"]}")
            to_set["technical_documentation_url"] = dataservice["endpoint_description_url"]

        result = get_db().dataservice.update_one(
            filter={
                "_id": dataservice["_id"],
            },
            update={"$set": to_set},
        )
        assert result.modified_count == 1
        assert result.matched_count == 1

    count = get_db().dataservice.update_many(
        {},
        {
            "$unset": {
                "endpoint_description_url": "",
                "is_restricted": "",
                "has_token": "",
            }
        },
    )
    print(f"Unset legacy fields on {count.modified_count} dataservices")

    log.info("Done")
