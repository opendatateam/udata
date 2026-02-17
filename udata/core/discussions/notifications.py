import logging
from enum import StrEnum, auto

from udata.api_fields import field, generate_fields
from udata.core.discussions.actions import discussions_for
from udata.core.discussions.api import discussion_fields
from udata.core.discussions.models import Discussion, Message
from udata.core.discussions.signals import on_discussion_deleted, on_discussion_message_deleted
from udata.features.notifications.actions import notifier
from udata.models import db

log = logging.getLogger(__name__)


class DiscussionStatus(StrEnum):
    NEW_DISCUSSION = auto()
    NEW_COMMENT = auto()
    CLOSED = auto()


@generate_fields()
class DiscussionNotificationDetails(db.EmbeddedDocument):
    status = field(
        db.EnumField(DiscussionStatus),
        readonly=True,
        auditable=False,
        filterable={},
    )
    # keep track of the message to show in the notification
    message_id = field(
        db.UUIDField(),
        readonly=True,
        auditable=False,
        filterable={},
    )
    discussion = field(
        db.ReferenceField(Discussion),
        readonly=True,
        nested_fields=discussion_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@notifier("discussion")
def discussions_notifications(user):
    """Notify user about open discussions"""
    notifications = []

    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = discussions_for(user).only("id", "created", "title", "subject")

    # Do not dereference subject (so it's a DBRef)
    # Also improve performances and memory usage
    for discussion in qs.no_dereference():
        notifications.append(
            (
                discussion.created,
                {
                    "id": discussion.id,
                    "title": discussion.title,
                    "subject": {
                        "id": discussion.subject["_ref"].id,
                        "type": discussion.subject["_cls"].lower(),
                    },
                },
            )
        )

    return notifications


@on_discussion_deleted.connect
def cleanup_discussion_notifications(discussion, **kwargs):
    """Clean up notifications when a discussion is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__discussion=discussion).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for discussion {discussion.id}: {e}")


@on_discussion_message_deleted.connect
def cleanup_message_notifications(discussion, message=None, **kwargs):
    """Clean up notifications when a message is deleted from a discussion"""
    from udata.features.notifications.models import Notification

    try:
        if message and isinstance(message, Message):
            Notification.objects(
                details__discussion=discussion, details__message_id=message.id
            ).delete()
    except Exception as e:
        log.error(
            f"Error cleaning up message notification for discussion {discussion.id}, message {getattr(message, 'id', None)}: {e}"
        )
