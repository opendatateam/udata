"""
This migration adds UUIDs to existing discussion messages that don't have one.
"""

import logging
import uuid

import click

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Adding UUIDs to discussion messages...")

    collection = db.discussion
    total_messages_updated = 0

    # Find all discussions that have at least one message without an id
    discussions_cursor = collection.find({"discussion.id": {"$exists": False}})
    discussions_list = list(discussions_cursor)

    with click.progressbar(discussions_list) as progress:
        for discussion in progress:
            messages = discussion.get("discussion", [])
            updated = False

            for message in messages:
                if "id" not in message:
                    message["id"] = uuid.uuid4()
                    updated = True
                    total_messages_updated += 1

            if updated:
                collection.update_one(
                    {"_id": discussion["_id"]}, {"$set": {"discussion": messages}}
                )

    log.info(f"Migration complete. {total_messages_updated} messages updated with UUIDs.")
