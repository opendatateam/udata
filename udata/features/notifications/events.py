import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mongoengine import Document, EmbeddedDocument

from udata.core.user.models import User
from udata.features.notifications.constants import (
    CATEGORY_BY_TYPE,
    MailCadence,
    NotificationCategory,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.settings import (
    decisions_for,
    default_enabled,
    subscribers_for,
)
from udata.mail import MailMessage

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recipient:
    """Somebody to notify, and why they are concerned.

    The reasons are not decoration. They pick the default this recipient falls back on
    when they never set anything, and they are what the bell and the mail footer show
    to explain where the notification comes from.

    `user` is a bare address when the recipient has no account yet — an invitation
    reaches its recipient before they are a user.
    """

    user: User | str
    reasons: frozenset[NotificationReason] = field(default_factory=frozenset)

    @property
    def key(self) -> Any:
        """What identifies the recipient across the several ways of reaching them."""
        return self.user.id if isinstance(self.user, User) else self.user


def merge_recipients(recipients: Iterable[Recipient]) -> list[Recipient]:
    """Fold recipients reached several times into one, keeping every reason.

    Somebody can be concerned twice over — owning the dataset a discussion is about
    and having answered in it — and both reasons matter: the most generous one decides
    what they get, and the footer has to name them all for its links to be honest.
    """
    merged: dict[Any, Recipient] = {}
    for recipient in recipients:
        existing = merged.get(recipient.key)
        merged[recipient.key] = (
            Recipient(existing.user, existing.reasons | recipient.reasons)
            if existing
            else recipient
        )
    return list(merged.values())


class NotificationEvent:
    """Something happened that users need to hear about.

    One subclass per `NotificationType`, holding the answers that used to be spread
    over a signal handler and a celery task: who is concerned and why, what the in-app
    notification says, what the email says, and what a setting about it can be scoped
    to.

    `via_app` and `via_mail` double as the channel decision: returning `None` means
    this recipient gets nothing on that channel. The base class opts out of both, so
    a subclass only declares the channels it actually uses.
    """

    type: NotificationType

    def recipients(self) -> list[Recipient]:
        raise NotImplementedError

    def scopes(self) -> list[Document]:
        """What a decision about this event can be taken on, most specific first.

        A discussion on a dataset of an organization yields `[discussion, dataset,
        organization]`, so that muting the thread, the dataset or the whole
        organization are three grains of the same setting. The global scope closes
        every chain and is implied, so it is not listed here.
        """
        return []

    def excluded(self) -> list[User]:
        """Who must never hear about this event, whatever they subscribed to.

        Typically whoever triggered it: being told about one's own comment is noise,
        and subscribing to a thread must not undo that.
        """
        return []

    def via_app(self, recipient: User) -> EmbeddedDocument | None:
        """The payload of the stored notification, or `None` to store nothing.

        A configurable type must always return one: the stored notification is what a
        digest is later built from, so returning `None` there would silently drop the
        mail of anybody who asked for a weekly summary.
        """
        return None

    def via_mail(self, recipient: User | str) -> MailMessage | None:
        return None

    @classmethod
    def sends_mail(cls) -> bool:
        """Whether this event has a mail to send at all.

        Asked before deferring one, so that a weekly digest never conjures a mail the
        immediate path does not send — a reuse creation reaches the bell only. Read off
        the class rather than off a built message: rendering can fail, and a failed
        render must not quietly cost somebody their digest entry.
        """
        return cls.via_mail is not NotificationEvent.via_mail

    @property
    def occurred_at(self) -> datetime:
        """When the event happened, which is not always when it is dispatched: a
        notification backfilled from an older subject keeps the subject's date."""
        return datetime.now(UTC)

    def dispatch(self) -> None:
        from udata.features.notifications.models import Notification

        category = CATEGORY_BY_TYPE.get(self.type)
        recipients = self._concerned(category)
        decisions = self._decisions(recipients, category)
        # Only the configurable types can wait. An invitation or a source pending
        # validation is an action to take: holding it for a week would be a bug, not a
        # setting.
        deferrable = category is not None

        for recipient in recipients:
            # An in-app notification needs an account to hang on, so an address with no
            # user behind it is reachable by email only.
            is_user = isinstance(recipient.user, User)
            wants_app = is_user and self._wants(
                recipient, NotificationChannel.APP, decisions, category
            )
            wants_mail = self._wants(recipient, NotificationChannel.MAIL, decisions, category)

            deferred = (
                wants_mail
                and deferrable
                and self.sends_mail()
                and is_user
                and recipient.user.mail_cadence is not MailCadence.IMMEDIATE
            )

            channels = []
            if wants_app:
                channels.append(NotificationChannel.APP)
            if deferred:
                channels.append(NotificationChannel.MAIL)

            # One failing recipient must not deprive the others of their notification.
            if channels:
                try:
                    details = self.via_app(recipient.user)
                    if details is not None:
                        Notification(
                            user=recipient.user,
                            type=self.type,
                            details=details,
                            reasons=sorted(recipient.reasons),
                            channels=channels,
                            created_at=self.occurred_at,
                        ).save()
                except Exception as e:
                    log.error(f"Could not notify {recipient.user} of {self.type}: {e}")

            if wants_mail and not deferred:
                try:
                    mail = self.via_mail(recipient.user)
                    if mail is not None:
                        mail.send(recipient.user)
                except Exception as e:
                    log.error(f"Could not email {recipient.user} about {self.type}: {e}")

    def _concerned(self, category: NotificationCategory | None) -> list[Recipient]:
        """Everybody this event reaches: those it concerns by itself, plus those who
        asked to be added, minus whoever it must never reach."""
        recipients = self.recipients()
        if category is not None:
            recipients = [
                *recipients,
                *(
                    Recipient(user, frozenset({NotificationReason.EXPLICIT_SUBSCRIBER}))
                    for user in subscribers_for(category, self.scopes())
                ),
            ]

        excluded = {user.id for user in self.excluded()}
        return [
            recipient for recipient in merge_recipients(recipients) if recipient.key not in excluded
        ]

    def _decisions(
        self, recipients: list[Recipient], category: NotificationCategory | None
    ) -> dict[NotificationChannel, dict[Any, bool]] | None:
        """What the recipients decided about this event, resolved once for all of them.

        `None` when the type carries no category, which is how the types that are not
        offered as a setting stay unconditional.
        """
        if category is None:
            return None

        users = [recipient.user for recipient in recipients if isinstance(recipient.user, User)]
        scopes = self.scopes()
        return {
            channel: decisions_for(users, category, scopes, channel)
            for channel in NotificationChannel
        }

    def _wants(
        self,
        recipient: Recipient,
        channel: NotificationChannel,
        decisions,
        category: NotificationCategory | None,
    ) -> bool:
        if decisions is None or category is None:
            # Either an action to take or the answer to a request this recipient made:
            # neither is something to opt out of.
            return True
        if not isinstance(recipient.user, User):
            # A bare address has no account to hang a setting on.
            return True
        decided = decisions[channel].get(recipient.user.id)
        return default_enabled(recipient.reasons, category) if decided is None else decided

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
