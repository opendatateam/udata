"""Migrate topic.datasets and topics.reuses to topic.elements"""

import logging

from bson import DBRef, ObjectId
from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing topics…")

    topics = get_db().topic.find()

    for topic in topics:
        log.info(f"Processing topic {topic['_id']}…")
        element_refs = []

        # Convert datasets to TopicElement documents
        for dataset_id in topic.get("datasets", []):
            element_id = ObjectId()
            element_doc = {
                "_id": element_id,
                "tags": [],
                "extras": {},
                "element": {"_cls": "Dataset", "_ref": DBRef("dataset", dataset_id)},
            }

            # Insert TopicElement document
            get_db().topic_element.insert_one(element_doc)

            # Add reference to elements list
            element_refs.append(element_id)

        # Convert reuses to TopicElement documents
        for reuse_id in topic.get("reuses", []):
            element_id = ObjectId()
            element_doc = {
                "_id": element_id,
                "tags": [],
                "extras": {},
                "element": {"_cls": "Reuse", "_ref": DBRef("reuse", reuse_id)},
            }

            # Insert TopicElement document
            get_db().topic_element.insert_one(element_doc)

            # Add reference to elements list
            element_refs.append(element_id)

        log.info(f"Topic: {topic.get('name', 'Unnamed')} (ID: {topic['_id']})")
        log.info(f"  - Converting {len(topic.get('datasets', []))} datasets")
        log.info(f"  - Converting {len(topic.get('reuses', []))} reuses")
        log.info(f"  - Total elements: {len(element_refs)}")

        # Update the topic document with references to TopicElement documents
        get_db().topic.update_one(
            {"_id": topic["_id"]},
            {
                "$set": {"elements": element_refs},
                "$unset": {"datasets": 1, "reuses": 1},  # Remove old fields
            },
        )
