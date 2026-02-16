import logging
from enum import StrEnum, auto

from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.discussions.actions import discussions_for
from udata.core.discussions.api import discussion_fields
from udata.core.discussions.models import Discussion
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
        ReferenceField(Discussion),
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
