"""
Drop `details.status` and `details.kind` from the stored notifications.

Both said what `Notification.type` now says, and nothing reads them any more. They are
removed from the documents as well as from the model: mongoengine refuses to load a
document holding a field its class no longer declares.

Runs after `2026-09-15-set-notification-type`, which derives the type from them.
"""

import logging

log = logging.getLogger(__name__)

FIELDS_BY_DETAILS = {
    "DiscussionNotificationDetails": "details.status",
    "ValidateHarvesterNotificationDetails": "details.status",
    "MembershipRequestNotificationDetails": "details.kind",
    "NewBadgeNotificationDetails": "details.kind",
}


def migrate(db):
    for details_cls, path in FIELDS_BY_DETAILS.items():
        result = db.notification.update_many(
            {"details._cls": details_cls, path: {"$exists": True}},
            {"$unset": {path: ""}},
        )
        log.info(f"Dropped {path} from {result.modified_count} {details_cls} notifications")
