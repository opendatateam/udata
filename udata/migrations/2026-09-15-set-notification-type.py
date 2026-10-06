"""
Set `Notification.type` from the details class and its discriminator field.

Additive on purpose: `details.status` and `details.kind` say the same thing and are
still what the front reads. They get dropped once it reads `type` instead.
"""

import logging
from collections import Counter

from udata.features.notifications.constants import NotificationType

log = logging.getLogger(__name__)

# `{"field": None}` matches both an explicit null and a missing field, so the
# entries below cover documents written before the discriminator got a value.
MAPPING = [
    (
        {"details._cls": "DiscussionNotificationDetails", "details.status": "new_discussion"},
        NotificationType.DISCUSSION_NEW,
    ),
    (
        {"details._cls": "DiscussionNotificationDetails", "details.status": "new_comment"},
        NotificationType.DISCUSSION_COMMENT,
    ),
    (
        {"details._cls": "DiscussionNotificationDetails", "details.status": "closed"},
        NotificationType.DISCUSSION_CLOSED,
    ),
    (
        {
            "details._cls": "MembershipRequestNotificationDetails",
            "details.kind": {"$in": ["request", None]},
        },
        NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED,
    ),
    (
        {"details._cls": "MembershipRequestNotificationDetails", "details.kind": "invitation"},
        NotificationType.ORGANIZATION_MEMBERSHIP_INVITED,
    ),
    (
        {"details._cls": "MembershipAcceptedNotificationDetails"},
        NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED,
    ),
    (
        {"details._cls": "MembershipRefusedNotificationDetails"},
        NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED,
    ),
    (
        {"details._cls": "NewBadgeNotificationDetails", "details.kind": "certified"},
        NotificationType.ORGANIZATION_BADGE_CERTIFIED,
    ),
    (
        {"details._cls": "NewBadgeNotificationDetails", "details.kind": "public-service"},
        NotificationType.ORGANIZATION_BADGE_PUBLIC_SERVICE,
    ),
    (
        {"details._cls": "NewBadgeNotificationDetails", "details.kind": "company"},
        NotificationType.ORGANIZATION_BADGE_COMPANY,
    ),
    (
        {"details._cls": "NewBadgeNotificationDetails", "details.kind": "association"},
        NotificationType.ORGANIZATION_BADGE_ASSOCIATION,
    ),
    (
        {"details._cls": "NewBadgeNotificationDetails", "details.kind": "local-authority"},
        NotificationType.ORGANIZATION_BADGE_LOCAL_AUTHORITY,
    ),
    ({"details._cls": "ReuseCreatedNotificationDetails"}, NotificationType.REUSE_CREATED),
    (
        {"details._cls": "DataserviceCreatedNotificationDetails"},
        NotificationType.DATASERVICE_CREATED,
    ),
    ({"details._cls": "TransferRequestNotificationDetails"}, NotificationType.TRANSFER_REQUESTED),
    (
        {
            "details._cls": "ValidateHarvesterNotificationDetails",
            "details.status": {"$in": ["pending", None]},
        },
        NotificationType.HARVEST_SOURCE_PENDING,
    ),
    (
        {"details._cls": "ValidateHarvesterNotificationDetails", "details.status": "accepted"},
        NotificationType.HARVEST_SOURCE_ACCEPTED,
    ),
    (
        {"details._cls": "ValidateHarvesterNotificationDetails", "details.status": "refused"},
        NotificationType.HARVEST_SOURCE_REFUSED,
    ),
]


def migrate(db):
    for query, notification_type in MAPPING:
        result = db.notification.update_many(
            {**query, "type": {"$exists": False}},
            {"$set": {"type": notification_type.value}},
        )
        log.info(f"{notification_type.value}: {result.modified_count} notifications")

    untyped = list(db.notification.find({"type": {"$exists": False}}, {"details": 1}))
    if untyped:
        # A discussion or badge notification whose discriminator was never set: the
        # type cannot be guessed, so it is left alone rather than defaulted to a wrong
        # one. Nothing cleans it up afterwards: `type` is required now, so the document
        # can no longer be saved, hence never marked as read nor purged. The breakdown
        # is there to decide what to do with it by hand.
        # `details` was never required, so a notification may carry none at all.
        breakdown = Counter(
            (d.get("_cls"), d.get("status"), d.get("kind"))
            for d in (n.get("details") or {} for n in untyped)
        )
        log.warning(f"{len(untyped)} notifications left untyped: {dict(breakdown)}")
