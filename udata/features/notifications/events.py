import logging
from datetime import UTC, datetime

from mongoengine import EmbeddedDocument

from udata.core.user.models import User
from udata.features.notifications.constants import NotificationType
from udata.mail import MailMessage

log = logging.getLogger(__name__)


class NotificationEvent:
    """Something happened that users need to hear about.

    One subclass per `NotificationType`, holding the three answers that used to be
    spread over a signal handler and a celery task: who is concerned, what the
    in-app notification says, and what the email says.

    `via_app` and `via_mail` double as the channel decision: returning `None` means
    this recipient gets nothing on that channel. The base class opts out of both, so
    a subclass only declares the channels it actually uses.
    """

    type: NotificationType

    def recipients(self) -> list[User | str]:
        """Users, plus the bare email addresses of people who have no account yet —
        an invitation reaches its recipient before they are a user."""
        raise NotImplementedError

    def via_app(self, recipient: User) -> EmbeddedDocument | None:
        return None

    def via_mail(self, recipient: User | str) -> MailMessage | None:
        return None

    @property
    def occurred_at(self) -> datetime:
        """When the event happened, which is not always when it is dispatched: a
        notification backfilled from an older subject keeps the subject's date."""
        return datetime.now(UTC)

    def dispatch(self) -> None:
        from udata.features.notifications.models import Notification

        for recipient in self.recipients():
            # One failing recipient must not deprive the others of their notification.
            try:
                # An in-app notification needs an account to hang on, so an address
                # with no user behind it is reachable by email only.
                details = self.via_app(recipient) if isinstance(recipient, User) else None
                if details is not None:
                    Notification(
                        user=recipient,
                        type=self.type,
                        details=details,
                        created_at=self.occurred_at,
                    ).save()
            except Exception as e:
                log.error(f"Could not notify {recipient} of {self.type}: {e}")

            try:
                mail = self.via_mail(recipient)
                if mail is not None:
                    mail.send(recipient)
            except Exception as e:
                log.error(f"Could not email {recipient} about {self.type}: {e}")

    def already_pending(self, recipient: User, **details) -> bool:
        """Whether the recipient still has an unhandled notification about the same
        thing. Used by the events that ask for an action: until it is taken, a second
        notification adds nothing."""
        from udata.features.notifications.models import Notification

        return (
            Notification.objects(
                user=recipient,
                handled_at=None,
                **{f"details__{name}": value for name, value in details.items()},
            ).first()
            is not None
        )
