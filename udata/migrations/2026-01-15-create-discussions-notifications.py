"""
Create DiscussionNotification for all existing discussions
"""

import logging
from datetime import datetime

import click

from udata.core.discussions.models import Discussion
from udata.core.discussions.notifications import DiscussionNotificationDetails, DiscussionStatus
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import Notification

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing existing discussions for notifications...")

    created_count = 0

    # Only process discussions created after 01/01/2026
    discussions = Discussion.objects(closed=None, created__gte=datetime(2026, 1, 1)).order_by(
        "-discussion.posted_on"
    )
    count = discussions.count()

    with click.progressbar(reversed(discussions), length=count) as progress:
        for discussion in progress:
            try:
                existing = Notification.objects(details__discussion=discussion).first()
                if not existing:
                    if len(discussion.discussion) > 1:
                        # Add NEW_COMMENT notifications for the last message
                        last_comment = discussion.discussion[-1]
                        sender = last_comment.posted_by
                        notification_type = NotificationType.DISCUSSION_COMMENT
                        # Superseded by `type`, kept until the front reads it
                        status = DiscussionStatus.NEW_COMMENT
                        message_id = str(last_comment.id)
                    else:
                        # Add NEW_DISCUSSION notifications if no reply yet
                        sender = discussion.user
                        notification_type = NotificationType.DISCUSSION_NEW
                        status = DiscussionStatus.NEW_DISCUSSION
                        message_id = None

                    for recipient in discussion.owner_recipients():
                        if sender and recipient.key == sender.id:
                            continue
                        Notification(
                            user=recipient.user,
                            type=notification_type,
                            reasons=sorted(recipient.reasons),
                            details=DiscussionNotificationDetails(
                                status=status, message_id=message_id, discussion=discussion
                            ),
                        ).save()
                        created_count += 1
            except Exception as e:
                log.error(f"Error creating notification for discussion {discussion.id}: {e}")

    log.info(f"Created {created_count} DiscussionNotifications")
