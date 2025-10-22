"""Migrate topic.datasets and topics.reuses to topic.elements with TopicElement.topic references"""

import logging

from bson import DBRef, ObjectId
from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing topics…")

    topics = get_db().topic.find()

    for topic in topics:
        log.info(f"Processing topic {topic['_id']}…")
        total_elements = 0

        # Convert datasets to TopicElement documents
        for dataset_id in topic.get("datasets", []):
            element_doc = {
                "_id": ObjectId(),
                "tags": [],
                "extras": {},
                "element": {"_cls": "Dataset", "_ref": DBRef("dataset", dataset_id)},
                "topic": topic["_id"],  # Reference to the topic
            }

            # Insert TopicElement document
            get_db().topic_element.insert_one(element_doc)
            total_elements += 1

        # Convert reuses to TopicElement documents
        for reuse_id in topic.get("reuses", []):
            element_doc = {
                "_id": ObjectId(),
                "tags": [],
                "extras": {},
                "element": {"_cls": "Reuse", "_ref": DBRef("reuse", reuse_id)},
                "topic": topic["_id"],  # Reference to the topic
            }

            # Insert TopicElement document
            get_db().topic_element.insert_one(element_doc)
            total_elements += 1

        log.info(f"Topic: {topic.get('name', 'Unnamed')} (ID: {topic['_id']})")
        log.info(f"  - Converting {len(topic.get('datasets', []))} datasets")
        log.info(f"  - Converting {len(topic.get('reuses', []))} reuses")
        log.info(f"  - Total elements: {total_elements}")

        # Remove old fields from topic document
        get_db().topic.update_one(
            {"_id": topic["_id"]},
            {
                "$unset": {"datasets": 1, "reuses": 1},  # Remove old fields
            },
        )
