import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bson import ObjectId
from mongoengine import Document, EmbeddedDocument

from udata.core.user.models import User
from udata.features.notifications.constants import (
    REASON_BY_ORGANIZATION_ROLE,
    TYPES_REQUIRING_ACTION,
    MailCadence,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.mails import settings_footer
from udata.features.notifications.settings import (
    readable_by,
    resolve,
    rules_for,
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


def responsible_recipients(subject) -> list[Recipient]:
    """Who is answerable for a subject, and on what ground: its owner, or the members of
    its organization, or of the organization it is.

    Partial editors are scoped to the objects handed to them: belonging to an
    organization whose datasets one cannot even edit is not a reason to hear about
    them. Everybody else, editors included, is concerned by the whole organization;
    whether that makes them hear about it is for their rules to say.
    """
    # Not at the top: `Assignment` resolves the models it can point to when it is
    # declared, and `Reuse` is not registered yet when this module loads.
    from udata.core.organization.assignment import Assignment
    from udata.core.organization.models import Organization

    if isinstance(subject, Organization):
        # The organization itself concerns all of its members, whatever was assigned to
        # them.
        return [Recipient.from_member(member) for member in subject.members]

    organization = getattr(subject, "organization", None)
    if organization:
        assigned = {assignment.user.id for assignment in Assignment.objects(subject=subject)}
        return [
            Recipient.from_member(member)
            for member in organization.members
            if member.role != "partial_editor" or member.user.id in assigned
        ]
    if getattr(subject, "owner", None):
        return [Recipient(subject.owner, frozenset({NotificationReason.OWNER}))]
    return []


def subject_scopes(subject) -> list[Document]:
    """What a rule about this subject can be taken on, most specific first: a thread,
    then what it is about, then the organization behind it."""
    from udata.core.discussions.models import Discussion

    if isinstance(subject, Discussion):
        return [subject, *subject_scopes(subject.subject)]
    organization = getattr(subject, "organization", None)
    return [subject, organization] if organization else [subject]


def event_chain(event: str | None) -> list[str]:
    """What a rule about this event can name, from the narrowest to the broadest: the
    type itself, then each of its dotted prefixes. `discussion.comment` yields
    `["discussion.comment", "discussion"]`; a rule naming no event covers them all.

    Grouping by prefix rather than by class keeps what a rule means apart from how the
    events share their code: refactoring a base class must not change who hears what.
    """
    if not event:
        return []
    parts = event.split(".")
    return [".".join(parts[:length]) for length in range(len(parts), 0, -1)]


def is_event_name(event: str) -> bool:
    """Whether a rule can name `event`: a notification type, or a prefix of some."""
    return any(type == event or type.startswith(f"{event}.") for type in NotificationType)


class NotificationEvent:
    """Something happened that users need to hear about.

    One subclass per `NotificationType`, holding everything about it in one place: who
    is concerned and why, what the in-app notification says, what the email says, and
    what a setting about it can be scoped to.

    `via_app` and `via_mail` double as the channel decision: returning `None` means
    this recipient gets nothing on that channel. The base class opts out of both, so
    a subclass only declares the channels it actually uses.

    Every event goes through the user's rules, except an action to take (an invitation,
    a source to validate): leaving it unanswered would be a bug, not a setting. What the
    settings screen offers to turn off is for the front to decide.
    """

    type: NotificationType
    # An answer addressed to one person ("your request was accepted") is not news about
    # its subject: following the subject must not bring it in. Its scopes still let the
    # recipient silence it.
    reaches_subscribers: bool = True

    @property
    def requires_action(self) -> bool:
        return self.type in TYPES_REQUIRING_ACTION

    @property
    def subject(self):
        """What the event is about, as the mail footer names it."""
        return None

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

    # How a digest counts this event ("3 new comments"), or `None` to mail it at once
    # whatever the cadence: an action to take (an invitation, a source pending
    # validation) cannot wait a week, and a rare event (a badge, the answer to one's
    # request) is no flood worth holding back.
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
                    mail = self._mail(recipient)
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
        if self.requires_action or not self.reaches_subscribers:
            return []
        return [
            Recipient(user, frozenset({reason}))
            for user, reason in subscribers_for(event_chain(self.type), self.scopes())
            if self.subject is None or readable_by(user, self.subject)
        ]

    def _mail(self, recipient: Recipient) -> MailMessage | None:
        """Something one can turn off says why it was sent, and where to turn it off."""
        mail = self.via_mail(recipient.user)
        if mail is not None and not self.requires_action:
            mail.footer = settings_footer(recipient.reasons, self.subject)
        return mail

    def _channels(
        self, recipients: list[Recipient]
    ) -> dict[ObjectId | str, set[NotificationChannel]]:
        """The channels each recipient is reached through, by recipient key: what their
        rules leave of this event (see `resolve`)."""
        if self.requires_action:
            return {recipient.key: set(NotificationChannel) for recipient in recipients}

        events, scopes = event_chain(self.type), self.scopes()
        users = [recipient.user for recipient in recipients if isinstance(recipient.user, User)]
        rules = rules_for(users, events, scopes)
        # An address with no account behind it has no rules: an invitation is the only
        # thing reaching it, and an invitation is an action to take.
        return {
            recipient.key: resolve(rules.get(recipient.key, []), events, scopes, recipient.reasons)
            if isinstance(recipient.user, User) and not recipient.user.notifications_paused
            else set()
            for recipient in recipients
        }

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


def event_for_type(notification_type: NotificationType) -> type[NotificationEvent]:
    """The event class behind a stored notification, which the digest asks how to
    summarize it."""

    def walk(base):
        for subclass in base.__subclasses__():
            yield subclass
            yield from walk(subclass)

    # An event carrying several types (one per kind of badge) lists them in `types`.
    return next(
        event
        for event in walk(NotificationEvent)
        if notification_type in getattr(event, "types", {getattr(event, "type", None)})
    )
