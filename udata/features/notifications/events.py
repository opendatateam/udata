import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bson import ObjectId
from mongoengine import Document, EmbeddedDocument

from udata.core.user.models import User
from udata.features.notifications.constants import (
    REASON_BY_ORGANIZATION_ROLE,
    MailCadence,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.mails import settings_footer
from udata.features.notifications.settings import resolve, rules_for, subscribers_for
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

    @classmethod
    def from_member(cls, member) -> "Recipient":
        """An organization member, concerned on the ground of their role."""
        return cls(member.user, frozenset({REASON_BY_ORGANIZATION_ROLE[member.role]}))

    @property
    def key(self) -> ObjectId | str:
        """What identifies the recipient across the several ways of reaching them."""
        return self.user.id if isinstance(self.user, User) else self.user


def merge_recipients(recipients: Iterable[Recipient]) -> list[Recipient]:
    """Fold recipients reached several times into one, keeping every reason.

    Somebody can be concerned twice over — owning the dataset a discussion is about
    and having answered in it — and both reasons matter: the most generous one decides
    what they get, and the footer has to name them all for its links to be honest.
    """
    merged: dict[ObjectId | str, Recipient] = {}
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

    One subclass per `NotificationType`, holding everything about it in one place: who
    is concerned and why, what the in-app notification says, what the email says, and
    what a setting about it can be scoped to.

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

    # How a digest counts this event ("3 new comments"), or `None` when it cannot wait
    # for a digest and is mailed at once: an invitation or a source pending validation
    # is an action to take, and holding it for a week would be a bug, not a setting.
    digest_count: Callable[[int], str] | None = None

    @classmethod
    def digest_subject(cls, details) -> tuple[object, str]:
        """What a digest line is about, as a key to group on and a title: the digest
        writes one line per subject rather than one per notification."""
        raise NotImplementedError

    @property
    def occurred_at(self) -> datetime:
        """When the event happened, which is not always when it is dispatched: a
        notification backfilled from an older subject keeps the subject's date."""
        return datetime.now(UTC)

    def dispatch(self) -> None:
        from udata.features.notifications.models import Notification

        recipients = self._concerned()
        channels_by_recipient = self._channels(recipients)

        for recipient in recipients:
            # An in-app notification needs an account to hang on, so an address with no
            # user behind it is reachable by email only.
            is_user = isinstance(recipient.user, User)
            wanted = channels_by_recipient[recipient.key]
            wants_app = is_user and NotificationChannel.APP in wanted
            wants_mail = NotificationChannel.MAIL in wanted

            deferred = (
                wants_mail
                and self.digest_count is not None
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
                except Exception:
                    log.exception(f"Could not notify {recipient.user} of {self.type}")

            if wants_mail and not deferred:
                try:
                    mail = self._mail(recipient.user)
                    if mail is not None:
                        mail.send(recipient.user)
                except Exception:
                    log.exception(f"Could not email {recipient.user} about {self.type}")

    def _concerned(self) -> list[Recipient]:
        """Everybody this event reaches: those it concerns by itself, plus those who
        asked to be added, minus whoever it must never reach."""
        excluded = {user.id for user in self.excluded()}
        return [
            recipient
            for recipient in merge_recipients([*self.recipients(), *self._subscribers()])
            if recipient.key not in excluded
        ]

    def _subscribers(self) -> list[Recipient]:
        return []

    def _mail(self, recipient: User | str) -> MailMessage | None:
        return self.via_mail(recipient)

    def _channels(
        self, recipients: list[Recipient]
    ) -> dict[ObjectId | str, set[NotificationChannel]]:
        """The channels each recipient is reached through, by recipient key."""
        # Either an action to take or the answer to a request this recipient made:
        # neither is something to opt out of.
        return {recipient.key: set(NotificationChannel) for recipient in recipients}

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


class ConfigurableEvent(NotificationEvent):
    """An event users decide about, unlike an action to take or an answer to their own
    request.

    A rule names one of the classes of the event by its name, from the event itself up
    to the family it belongs to; a rule naming none covers every configurable event.
    Renaming one of these classes therefore needs a migration of
    `NotificationSetting.event`.
    """

    @classmethod
    def decision_events(cls) -> list[str]:
        """The class names a rule about this event can name, from the narrowest to the
        broadest."""
        return [
            klass.__name__
            for klass in cls.__mro__
            if issubclass(klass, ConfigurableEvent) and klass is not ConfigurableEvent
        ]

    def _mail(self, recipient):
        """Something one can turn off says where to."""
        mail = self.via_mail(recipient)
        if mail is not None:
            mail.footer = settings_footer()
        return mail

    def _subscribers(self):
        return [
            Recipient(user, frozenset({NotificationReason.EXPLICIT_SUBSCRIBER}))
            for user in subscribers_for(self.decision_events(), self.scopes())
        ]

    def _channels(self, recipients):
        """What the rules of each recipient leave of this event: see `resolve`."""
        events, scopes = self.decision_events(), self.scopes()
        users = [recipient.user for recipient in recipients if isinstance(recipient.user, User)]
        rules = rules_for(users, events, scopes)
        return {
            recipient.key: resolve(rules.get(recipient.key, []), events, scopes, recipient.reasons)
            if isinstance(recipient.user, User)
            else set()
            for recipient in recipients
        }


def concrete_events() -> list[type[NotificationEvent]]:
    """Every event that can be dispatched: the subclasses declaring a `type`, at any
    depth, leaving out the base classes a family shares."""

    def walk(base):
        for subclass in base.__subclasses__():
            yield subclass
            yield from walk(subclass)

    return [event for event in walk(NotificationEvent) if hasattr(event, "type")]


def configurable_events() -> list[type[ConfigurableEvent]]:
    return [event for event in concrete_events() if issubclass(event, ConfigurableEvent)]


def settable_events() -> set[str]:
    """Everything a rule can name: each configurable event and the families they
    belong to."""
    return {name for event in configurable_events() for name in event.decision_events()}


def event_for_type(notification_type: NotificationType) -> type[NotificationEvent]:
    return next(event for event in concrete_events() if event.type == notification_type)
