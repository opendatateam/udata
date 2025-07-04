import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Dataset collection - renaming harvest.created_at to harvest.issued_at")

    db = get_db()
    dataset_collection = db.dataset

    result = dataset_collection.update_many(
        {"resources.0": {"$exists": True}, "resources.harvest.created_at": {"$exists": True}},
        [
            {
                "$set": {
                    "resources": {
                        "$map": {
                            "input": "$resources",
                            "as": "r",
                            "in": {
                                "$mergeObjects": [
                                    "$$r",
                                    {
                                        "harvest": {
                                            "$mergeObjects": [
                                                "$$r.harvest",
                                                {
                                                    "issued_at": "$$r.harvest.created_at",
                                                },
                                            ]
                                        }
                                    },
                                ]
                            },
                        }
                    }
                }
            },
            {"$unset": "resources.harvest.created_at"},
        ],
    )
    log.info(f"{result.modified_count} Datasets processed.")
