"""Migrate topic.datasets and topics.reuses to topic.elements"""

import logging
import uuid

from bson import DBRef
from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing topics…")

    topics = get_db().topic.find()

    for topic in topics:
        log.info(f"Processing topic {topic['_id']}…")
        elements = []

        # Convert datasets to elements with DBRef
        for dataset_id in topic.get("datasets", []):
            elements.append(
                {
                    "_id": str(uuid.uuid4()),
                    "tags": [],
                    "extras": {},
                    "element": {"_cls": "Dataset", "_ref": DBRef("dataset", dataset_id)},
                }
            )

        # Convert reuses to elements with DBRef
        for reuse_id in topic.get("reuses", []):
            elements.append(
                {
                    "_id": str(uuid.uuid4()),
                    "tags": [],
                    "extras": {},
                    "element": {"_cls": "Reuse", "_ref": DBRef("reuse", reuse_id)},
                }
            )

        log.info(f"Topic: {topic.get('name', 'Unnamed')} (ID: {topic['_id']})")
        log.info(f"  - Converting {len(topic.get('datasets', []))} datasets")
        log.info(f"  - Converting {len(topic.get('reuses', []))} reuses")
        log.info(f"  - Total elements: {len(elements)}")

        # Update the topic document
        get_db().topic.update_one(
            {"_id": topic["_id"]},
            {
                "$set": {"elements": elements},
                "$unset": {"datasets": 1, "reuses": 1},  # Remove old fields
            },
        )
