import logging
from enum import StrEnum, auto

from mongoengine import EmbeddedDocument
from mongoengine.fields import EnumField, ReferenceField, UUIDField

from udata.api_fields import field, generate_fields
from udata.core.discussions import mails
from udata.core.discussions.models import Discussion, Message
from udata.core.discussions.signals import on_discussion_deleted, on_discussion_message_deleted
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.events import NotificationEvent

log = logging.getLogger(__name__)


class DiscussionStatus(StrEnum):
    NEW_DISCUSSION = auto()
    NEW_COMMENT = auto()
    CLOSED = auto()


# Superseded by `Notification.type`, kept until the front reads the type instead.
STATUSES_BY_TYPE = {
    NotificationType.DISCUSSION_NEW: DiscussionStatus.NEW_DISCUSSION,
    NotificationType.DISCUSSION_COMMENT: DiscussionStatus.NEW_COMMENT,
    NotificationType.DISCUSSION_CLOSED: DiscussionStatus.CLOSED,
}


@generate_fields()
class DiscussionNotificationDetails(EmbeddedDocument):
    # Superseded by `Notification.type`, kept until the front reads the type instead.
    status = field(
        EnumField(DiscussionStatus),
        readonly=True,
        auditable=False,
        filterable={},
    )
    # keep track of the message to show in the notification
    message_id = field(
        UUIDField(),
        readonly=True,
        auditable=False,
        filterable={},
    )
    discussion = field(
        ReferenceField(Discussion),
        readonly=True,
        nested_fields=Discussion.__read_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class DiscussionEvent(NotificationEvent):
    """Everyone who took part in the discussion, plus the people responsible for its
    subject, minus whoever triggered the event."""

    def __init__(self, discussion: Discussion):
        self.discussion = discussion

    @property
    def sender(self) -> User:
        """Whoever triggered the event, and therefore does not need to hear about it."""
        raise NotImplementedError

    def recipients(self):
        return self.discussion.owner_recipients(sender=self.sender)

    def scopes(self):
        """Muting one thread, one dataset or a whole organization are three grains of
        the same setting."""
        scopes = [self.discussion, self.discussion.subject]
        if getattr(self.discussion.subject, "organization", None):
            scopes.append(self.discussion.subject.organization)
        return scopes

    def via_app(self, recipient):
        return DiscussionNotificationDetails(
            discussion=self.discussion,
            status=STATUSES_BY_TYPE[self.type],
        )


class NewDiscussion(DiscussionEvent):
    type = NotificationType.DISCUSSION_NEW

    @property
    def sender(self):
        return self.discussion.user

    @property
    def occurred_at(self):
        return self.discussion.created

    def via_mail(self, recipient):
        return mails.new_discussion(self.discussion, self.discussion.notification_url)


class NewDiscussionComment(DiscussionEvent):
    type = NotificationType.DISCUSSION_COMMENT

    def __init__(self, discussion: Discussion, message: Message):
        super().__init__(discussion)
        self.message = message

    @property
    def sender(self):
        return self.message.posted_by

    @property
    def occurred_at(self):
        return self.message.posted_on

    def via_app(self, recipient):
        details = super().via_app(recipient)
        details.message_id = str(self.message.id)
        return details

    def via_mail(self, recipient):
        return mails.new_discussion_comment(
            self.discussion, self.message, self.discussion.notification_url
        )


class DiscussionClosed(DiscussionEvent):
    type = NotificationType.DISCUSSION_CLOSED

    def __init__(self, discussion: Discussion, message: Message | None):
        super().__init__(discussion)
        self.message = message

    @property
    def sender(self):
        return self.discussion.closed_by

    @property
    def occurred_at(self):
        return self.discussion.closed

    def via_mail(self, recipient):
        return mails.discussion_closed(
            self.discussion, self.message, self.discussion.notification_url
        )


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
