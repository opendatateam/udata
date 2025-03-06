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
    log.info("Preprocessing dataservices…")

    count = get_db().dataservice.update_many(
        filter={
            "$or": [
                {"is_restricted": None},
                {"is_restricted": {"$exists": False}},
            ]
        },
        update={"$set": {"is_restricted": False}},
    )
    log.info(
        f"\tConverted {count.modified_count} dataservices from `is_restricted=None` to `is_restricted=False`"
    )

    count = get_db().dataservice.update_many(
        filter={
            "$or": [
                {"has_token": None},
                {"has_token": {"$exists": False}},
            ]
        },
        update={"$set": {"has_token": False}},
    )
    log.info(
        f"\tConverted {count.modified_count} dataservices from `has_token=None` to `has_token=False`"
    )

    for dataservice in get_db().dataservice.find({"is_restricted": True, "has_token": False}):
        log.info(
            f"\tDataservice #{dataservice['_id']} {dataservice['title']} is restricted but without token. (will be set to access_type={DATASERVICE_ACCESS_TYPE_RESTRICTED})"
        )

    log.info("Processing dataservices…")

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": True,
            # `has_token` could be True or False, we don't care
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_RESTRICTED}},
    )
    log.info(
        f"\t{count.modified_count} restricted dataservices to DATASERVICE_ACCESS_TYPE_RESTRICTED"
    )

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": False,
            "has_token": True,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT}},
    )
    log.info(
        f"\t{count.modified_count} dataservices not restricted but with token to DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT"
    )

    count = get_db().dataservice.update_many(
        filter={
            "is_restricted": False,
            "has_token": False,
        },
        update={"$set": {"access_type": DATASERVICE_ACCESS_TYPE_OPEN}},
    )
    log.info(f"\t{count.modified_count} open dataservices to DATASERVICE_ACCESS_TYPE_OPEN")

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
            or dataservice["endpoint_description_url"].endswith(".yml")
            or dataservice["endpoint_description_url"].endswith("?format=openapi-json")
            or "getcapabilities" in dataservice["endpoint_description_url"].lower()
            or "getresourcedescription" in dataservice["endpoint_description_url"].lower()
            or dataservice["endpoint_description_url"].startswith(
                "https://api.insee.fr/catalogue/api-docs/carbon.super"
            )
        ):
            # log.info(f"[MACHINE] {dataservice["endpoint_description_url"]}")
            to_set["machine_documentation_url"] = dataservice["endpoint_description_url"]
        else:
            # log.info(f"[ HUMAN ] {dataservice["endpoint_description_url"]}")
            to_set["technical_documentation_url"] = dataservice["endpoint_description_url"]

        result = get_db().dataservice.update_one(
            filter={
                "_id": dataservice["_id"],
            },
            update={"$set": to_set},
        )
        assert result.modified_count == 1
        assert result.matched_count == 1

    log.info("Postprocessing dataservices…")

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
    log.info(f"\tUnset legacy fields on {count.modified_count} dataservices")

    log.info("Done")
