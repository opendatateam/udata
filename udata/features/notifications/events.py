import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bson import ObjectId
from flask_babel import LazyString
from mongoengine import Document, EmbeddedDocument

from udata.core.discussions.models import Discussion
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.constants import (
    REASON_BY_ORGANIZATION_ROLE,
    TYPES_REQUIRING_ACTION,
    MailCadence,
    NotificationReason,
    NotificationType,
    event_chain,
)
from udata.features.notifications.mails import settings_footer, way_out
from udata.features.notifications.settings import (
    REASON_BY_ORIGIN,
    follows,
    readable_by,
    resolve,
    rules_for,
)
from udata.i18n import lazy_gettext as _
from udata.mail import Link, MailCTA, MailMessage

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recipient:
    """Somebody to notify, and why they are concerned.

    The reasons are not decoration. They pick the default this recipient falls back on
    when they never set anything, and they are what the bell and the mail footer show
    to explain where the notification comes from.

    `user` is a bare address when the recipient has no account yet — an invitation
    reaches its recipient before they are a user.

    `followed` is what the recipient follows that brought them in, when a follow did: the
    thread, the dataset or the organization. The mail names it rather than the subject
    of the event, which the recipient may never have followed as such.
    """

    user: User | str
    reasons: frozenset[NotificationReason] = field(default_factory=frozenset)
    followed: Document | None = None

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
            Recipient(
                existing.user,
                existing.reasons | recipient.reasons,
                existing.followed or recipient.followed,
            )
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


def discussion_recipients(discussion) -> list[Recipient]:
    """Who should hear about a discussion, and on what ground: whoever took part in it,
    and whoever is answerable for its subject.

    Somebody can qualify twice over — having answered in a thread about a dataset of the
    organization they administer — and both grounds are kept: the most generous one
    decides what they get, and an explanation naming only one of them would offer a way
    out that does not stop anything.
    """
    return merge_recipients(
        [
            *(
                Recipient(message.posted_by, frozenset({NotificationReason.DISCUSSION_PARTICIPANT}))
                for message in discussion.discussion
            ),
            *responsible_recipients(discussion.subject),
        ]
    )


def subject_scopes(subject) -> list[Document]:
    """What a rule about this subject can be taken on, most specific first: a thread,
    then what it is about, then the organization behind it."""
    if isinstance(subject, Discussion):
        return [subject, *subject_scopes(subject.subject)]
    organization = getattr(subject, "organization", None)
    return [subject, organization] if organization else [subject]


class NotificationEvent:
    """Something happened that users need to hear about.

    One subclass per `NotificationType`, holding everything about it in one place: who
    is concerned and why, what the in-app notification says, what the email says, and
    what a setting about it can be scoped to.

    `via_app` and `via_mail` double as the channel decision: returning `None` means
    this recipient gets nothing on that channel. The base class opts out of both, so
    a subclass only declares the channels it actually uses. The user's rules only say
    whether they hear about it, never through which channel.

    Every event goes through the user's rules, except an action to take (an invitation,
    a source to validate): leaving it unanswered would be a bug, not a setting. What the
    settings screen offers to turn off is for the front to decide.
    """

    type: NotificationType
    # What the type is called where one can turn it off, an action to take excepted.
    label: LazyString | None = None
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
        return subject_scopes(self.subject) if self.subject is not None else []

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
    def digest_subject(cls, details) -> tuple[object, Link]:
        """What a digest line is about, as a key to group on and a link to it: the
        digest writes one line per subject rather than one per notification."""
        raise NotImplementedError

    @property
    def occurred_at(self) -> datetime:
        """When the event happened, which is not always when it is dispatched: a
        notification backfilled from an older subject keeps the subject's date."""
        return datetime.now(UTC)

    def dispatch(self) -> None:
        from udata.features.notifications.models import Notification

        recipients = self._concerned()
        heard = self._heard(recipients)

        for recipient in recipients:
            if recipient.key not in heard:
                continue
            # An in-app notification needs an account to hang on, so an address with no
            # user behind it is reachable by email only.
            is_user = isinstance(recipient.user, User)
            deferred = (
                is_user
                and self.digest_count is not None
                and recipient.user.mail_cadence is not MailCadence.IMMEDIATE
            )

            # One failing recipient must not deprive the others of their notification.
            if is_user:
                try:
                    details = self.via_app(recipient.user)
                    if details is not None:
                        Notification(
                            user=recipient.user,
                            type=self.type,
                            details=details,
                            reasons=sorted(recipient.reasons),
                            mail_pending=deferred,
                            created_at=self.occurred_at,
                        ).save()
                except Exception:
                    log.exception(f"Could not notify {recipient.user} of {self.type}")

            if not deferred:
                try:
                    mail = self._mail(recipient)
                    if mail is not None:
                        mail.send(recipient.user)
                except Exception:
                    log.exception(f"Could not email {recipient.user} about {self.type}")

    def _concerned(self) -> list[Recipient]:
        """Everybody this event reaches: those it concerns by itself, plus those who
        asked to be added, minus whoever it must never reach. A deleted account keeps its
        rules and may still own subjects, but nobody is behind it any more."""
        excluded = {user.id for user in self.excluded()}
        return [
            recipient
            for recipient in merge_recipients([*self.recipients(), *self._subscribers()])
            if recipient.key not in excluded
            and not (isinstance(recipient.user, User) and recipient.user.deleted)
        ]

    def _subscribers(self) -> list[Recipient]:
        """Who follows one of the scopes of this event, with the reason their follow gives.

        The other direction of the table: `rules_for` filters people the event already
        reaches, this one brings in those it would never have reached. Without it,
        somebody outside an organization could follow a subject and never hear about it.
        """
        scopes = self.scopes()
        if self.requires_action or not self.reaches_subscribers or not scopes:
            return []
        # The most specific first, so that a user following both a thread and its dataset
        # is told about the thread.
        rank = {scope.pk: index for index, scope in enumerate(scopes)}
        settings = sorted(
            follows(event_chain(self.type), scopes)
            .only("user", "scope", "origin")
            .select_related(),
            key=lambda setting: rank[setting.scope.pk],
        )
        return [
            Recipient(setting.user, frozenset({REASON_BY_ORIGIN[setting.origin]}), setting.scope)
            for setting in settings
            if self.subject is None or readable_by(setting.user, self.subject)
        ]

    def _mail(self, recipient: Recipient) -> MailMessage | None:
        """Something one can turn off says why it was sent, and how to turn it off."""
        mail = self.via_mail(recipient.user)
        if mail is not None and not self.requires_action:
            mail.footer = settings_footer(
                recipient.reasons, self.subject, self.ways_out(), followed=recipient.followed
            )
        return mail

    def ways_out(self) -> list[MailCTA]:
        """What the mail offers to stop, the same as the menu of the notification in the
        bell: its subject, then this type of notification anywhere."""
        ways_out = []
        if self.subject is not None:
            ways_out.append(
                way_out(
                    _("Receive nothing more about %(subject)s", subject=str(self.subject)),
                    scope=self.subject,
                )
            )
        ways_out.append(
            way_out(_("Stop receiving: %(type)s", type=self.label), event=self.labelled_event)
        )
        return ways_out

    @property
    def labelled_event(self) -> str:
        """What `label` names, and stopping it turns off: the type, or the family of types
        an event class stands for (the five badges)."""
        return self.type

    def _heard(self, recipients: list[Recipient]) -> set[ObjectId | str]:
        """The keys of the recipients their rules let hear about this event (see
        `resolve`)."""
        if self.requires_action:
            return {recipient.key for recipient in recipients}

        events, scopes = event_chain(self.type), self.scopes()
        users = [recipient.user for recipient in recipients if isinstance(recipient.user, User)]
        rules = rules_for(users, events, scopes)
        # An address with no account behind it has no rules: an invitation is the only
        # thing reaching it, and an invitation is an action to take.
        return {
            recipient.key
            for recipient in recipients
            if isinstance(recipient.user, User)
            and not recipient.user.notifications_paused
            and resolve(rules.get(recipient.key, []), events, scopes, recipient.reasons)
        }

    def already_pending(self, recipient: User, **details) -> bool:
        """Whether the recipient still has an unhandled notification about the same
        thing. Used by the events that ask for an action: until it is taken, a second
        notification adds nothing."""
        return (
            self._notifications_about(recipient, details).filter(handled_at=None).first()
            is not None
        )

    def already_notified(self, recipient: User, **details) -> bool:
        """Whether the recipient was notified about the same thing, read or not, as long
        as the notification is kept: a handled one goes after
        `DAYS_AFTER_NOTIFICATION_EXPIRED` days, and an announcement can then come back.
        Used by the announcements that must not repeat whenever their trigger does."""
        return self._notifications_about(recipient, details).first() is not None

    @staticmethod
    def _notifications_about(recipient: User, details: dict):
        from udata.features.notifications.models import Notification

        return Notification.objects(
            user=recipient, **{f"details__{name}": value for name, value in details.items()}
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
