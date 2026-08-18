"""
Accepting a transfer used to move a dataset or a dataservice to its new owner while leaving
its contact points behind, so those objects ended up referencing contact points owned by
someone else. `Dataset.clean` and `Dataservice.clean` now reject that state, which would
make every subsequent save of those objects fail.
"""

import logging

from udata.core.contact_point.models import ContactPoint
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)

MISMATCHED_CONTACT_POINTS = [
    {"$match": {"contact_points.0": {"$exists": True}}},
    {
        "$lookup": {
            "from": ContactPoint._get_collection_name(),
            "localField": "contact_points",
            "foreignField": "_id",
            "as": "contacts",
        }
    },
    {
        "$addFields": {
            "mismatched": {
                "$filter": {
                    "input": "$contacts",
                    "cond": {
                        "$or": [
                            {
                                "$ne": [
                                    {"$ifNull": ["$$this.organization", None]},
                                    {"$ifNull": ["$organization", None]},
                                ]
                            },
                            {
                                "$ne": [
                                    {"$ifNull": ["$$this.owner", None]},
                                    {"$ifNull": ["$owner", None]},
                                ]
                            },
                        ]
                    },
                }
            }
        }
    },
    {"$match": {"mismatched.0": {"$exists": True}}},
    {"$project": {"_id": 1}},
]


def migrate(db):
    for model in (Dataset, Dataservice):
        ids = [
            document["_id"]
            for document in db[model._get_collection_name()].aggregate(MISMATCHED_CONTACT_POINTS)
        ]

        fixed = 0
        for document in model.objects(id__in=ids):
            owner = document.organization or document.owner
            if not owner:
                # Nothing to resolve the contact points against. Ownerless objects are not
                # what transfers produce, so leave them to be looked at by hand.
                log.warning(f"{model.__name__} #{document.id} has contact points but no owner.")
                continue
            document.contact_points = [
                contact_point.for_owner(owner) for contact_point in document.contact_points
            ]
            document.save()
            fixed += 1

        log.info(f"{fixed} {model.__name__.lower()}s given contact points of their own owner.")
