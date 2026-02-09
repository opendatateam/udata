"""
Create DiscussionNotification for all existing discussions
"""

import logging
from datetime import datetime

import click

from udata.core.discussions.models import Discussion
from udata.core.discussions.notifications import DiscussionNotificationDetails, DiscussionStatus
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
            print(discussion)
            try:
                existing = Notification.objects(details__discussion=discussion).first()
                if not existing:
                    # Add NEW_COMMENT notifications for the last message
                    if len(discussion.discussion) > 1:
                        last_comment = discussion.discussion[-1]

                        recipients = discussion.owner_recipients(sender=last_comment.posted_by)

                        for user in recipients:
                            notification = Notification(
                                user=user,
                                details=DiscussionNotificationDetails(
                                    status=DiscussionStatus.NEW_COMMENT,
                                    message_id=str(last_comment.id),
                                    discussion=discussion,
                                ),
                            )
                            notification.save()
                            created_count += 1
                    else:
                        # Add NEW_DISCUSSION notifications if no reply yet
                        recipients = discussion.owner_recipients(sender=discussion.user)

                        for user in recipients:
                            notification = Notification(
                                user=user,
                                details=DiscussionNotificationDetails(
                                    status=DiscussionStatus.NEW_DISCUSSION,
                                    discussion=discussion,
                                ),
                            )
                            notification.save()
                            created_count += 1
            except Exception as e:
                log.error(f"Error creating notification for discussion {discussion.id}: {e}")

    log.info(f"Created {created_count} DiscussionNotifications")
