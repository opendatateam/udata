from datetime import UTC, datetime

from udata.core.discussions.notifications import DiscussionNotificationDetails, DiscussionStatus
from udata.features.notifications.models import Notification
from udata.tasks import connect, get_logger

from . import mails
from .constants import NOTIFY_DISCUSSION_SUBJECTS
from .models import Discussion
from .signals import on_discussion_closed, on_new_discussion, on_new_discussion_comment

log = get_logger(__name__)


def _resolve_notification_url(discussion):
    """Return the notification URL, or `None` to skip when the subject type is
    unrecognised.

    Every `notify_*` task sends to the subject's owner; an unrecognised subject
    type has no recipients and must be skipped.
    """
    if not isinstance(discussion.subject, NOTIFY_DISCUSSION_SUBJECTS):
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))
        return None
    return discussion.notification_url


@connect(on_new_discussion, by_id=True)
def notify_new_discussion(discussion_id):
    discussion = Discussion.objects.get(pk=discussion_id)
    url = _resolve_notification_url(discussion)
    if url is None:
        return

    recipients = discussion.owner_recipients(sender=discussion.user)
    mails.new_discussion(discussion, url).send(recipients)
    for recipient in recipients:
        notification = Notification(
            created_at=discussion.created,
            user=recipient,
            details=DiscussionNotificationDetails(
                status=DiscussionStatus.NEW_DISCUSSION,
                discussion=discussion,
            ),
        )
        notification.save()


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    url = _resolve_notification_url(discussion)
    if url is None:
        return

    recipients = discussion.owner_recipients(sender=message.posted_by)
    mails.new_discussion_comment(discussion, message, url).send(recipients)

    previous_notifications = Notification.objects.filter(
        user=message.posted_by, details__discussion=discussion
    )
    for notification in previous_notifications:
        notification.handled_at = datetime.now(UTC)
        notification.save()

    for recipient in recipients:
        notification = Notification(
            created_at=message.posted_on,
            user=recipient,
            details=DiscussionNotificationDetails(
                status=DiscussionStatus.NEW_COMMENT,
                message_id=str(message.id),
                discussion=discussion,
            ),
        )
        notification.save()


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message] if message else None
    url = _resolve_notification_url(discussion)
    if url is None:
        return

    recipients = discussion.owner_recipients(sender=discussion.closed_by)
    mails.discussion_closed(discussion, message, url).send(recipients)

    previous_notifications = Notification.objects.filter(
        user=discussion.closed_by, details__discussion=discussion
    )
    for notification in previous_notifications:
        notification.handled_at = datetime.now(UTC)
        notification.save()

    for recipient in recipients:
        notification = Notification(
            created_at=discussion.closed,
            user=recipient,
            details=DiscussionNotificationDetails(
                status=DiscussionStatus.CLOSED,
                discussion=discussion,
            ),
        )
        notification.save()
