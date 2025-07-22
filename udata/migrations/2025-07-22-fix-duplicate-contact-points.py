"""
This migration computes the dataset last_udpate property that is now stored in the model.
It simply iterates on dataset and save them, triggering the clean() method where the last_update compute ocurs.
"""

import logging

from udata.core.contact_point.models import ContactPoint
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Fixing contact points")

    duplicates = list(
        ContactPoint.objects.aggregate(
            {
                "$group": {
                    "_id": {
                        "name": "$name",
                        "email": "$email",
                        "contact_form": "$contact_form",
                        "role": "$role",
                        "owner": "$owner",
                        "organization": "$organization",
                    },
                    "count": {"$sum": 1},
                    "ids": {"$push": "$_id"},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        )
    )

    removed_count = 0
    for group in duplicates:
        ids = group["ids"]
        keep = ids[0]
        remove_ids = ids[1:]

        Dataset.objects(contact_points__in=remove_ids).update(add_to_set__contact_points=keep)
        Dataset.objects(contact_points__in=remove_ids).update(pull_all__contact_points=remove_ids)

        Dataservice.objects(contact_points__in=remove_ids).update(add_to_set__contact_points=keep)
        Dataservice.objects(contact_points__in=remove_ids).update(
            pull_all__contact_points=remove_ids
        )

        removed_count += ContactPoint.objects(id__in=remove_ids).delete()

    log.info(f"Done. {removed_count} contact points removed")
