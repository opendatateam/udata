"""
This migration adds UUIDs to existing discussion messages that don't have one.
"""

import logging

import click

from udata.core.discussions.models import Discussion

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Adding UUIDs to discussion messages...")

    # Find all discussions that have at least one message without an id
    discussions = Discussion.objects(
        __raw__={"discussion": {"$elemMatch": {"id": {"$exists": False}}}}
    )
    count = discussions.count()

    with click.progressbar(discussions, length=count) as progress:
        for discussion in progress:
            discussion._mark_as_changed("discussion")
            discussion.save()

    log.info(f"Migration complete. {count} discussions updated.")
