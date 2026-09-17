"""
Give every existing notification the channel it was delivered through.

`Notification.channels` now says which channels still have to carry a notification,
and the bell only lists the ones holding `app`. Rows written before the field existed
have none, so they would vanish from every user's bell — they were all in-app
notifications, and their mail, if any, went out at the time.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Setting channels on existing notifications...")

    result = db.notification.update_many(
        {"channels": {"$exists": False}},
        {"$set": {"channels": ["app"]}},
    )

    log.info(f"Set channels on {result.modified_count} notifications")
