from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from bson import ObjectId
from mongoengine import CASCADE, Document, Q, ValidationError
from mongoengine.fields import (
    BooleanField,
    EnumField,
    GenericReferenceField,
    ReferenceField,
    StringField,
)

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.core.discussions.constants import DISCUSSION_SUBJECTS
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationChannel, NotificationReason
from udata.mongo.document import UDataDocument

# Everything a rule can be scoped to. Anything an event can name in its `scopes()`
# belongs here, which is why a discussion sits next to the objects that carry them:
# muting a single thread is the finest useful grain.
NOTIFICATION_SCOPES = ("Organization", "Discussion", *DISCUSSION_SUBJECTS)

# Only reached by actions to take, which are not configurable: a rule about it would be
# stored and never read.
CONFIGURABLE_REASONS = tuple(
    reason for reason in NotificationReason if reason is not NotificationReason.SYSADMIN
)


@generate_fields()
class NotificationSetting(UDataDocument):
    """One rule a user set about their notifications.

    Every dimension is optional, and leaving one out means "whatever it is": no scope
    is everywhere, no event is every configurable notification, no reason is whatever
    concerns the user, no channel is whether they are concerned at all. The settings
    screen only offers some combinations; the model holds them all, so that a new
    screen never needs a new model.

    - follow a thread: scope = the thread, event = `DiscussionEvent`, yes
    - ignore a dataset: scope = the dataset, no
    - "as an editor, never": reason = editor, no
    - "as an administrator, in the app only": reason = administrator, channel = mail, no
    - "no mail for the answers": event = `NewDiscussionComment`, channel = mail, no

    See `resolve` for which rule wins when several apply.
    """

    # Not exposed: the API only ever lists and writes the current user's rules.
    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    # Read back as a bare `{class, id}`: a rule can name an object its author can no
    # longer see, and its title must not travel with it.
    scope = field(
        GenericReferenceField(choices=NOTIFICATION_SCOPES),
        nested_fields=api.model_reference,
        description="The subject the rule is about, null for everywhere",
    )
    event = field(
        StringField(),
        description="A configurable event class (a single event or a family of them), "
        "null for every configurable notification",
    )
    reason = field(
        EnumField(NotificationReason),
        description="Why the user is concerned, null for whatever the reason",
    )
    channel = field(
        EnumField(NotificationChannel),
        description="Where the user is reached, null to decide whether they are concerned at all",
    )
    enabled = field(BooleanField(required=True))

    meta = {
        "indexes": [
            {"fields": ["user", "scope", "event", "reason", "channel"], "unique": True},
            # `subscribers_for` looks across every user, once per configurable event.
            ["scope", "event", "enabled"],
        ],
    }

    def clean(self):
        # `events` builds on this module, hence the import at call time.
        from udata.features.notifications.events import settable_events

        super().clean()
        if self.event is not None and self.event not in settable_events():
            raise ValidationError(f"{self.event} is not a configurable notification")
        if self.reason is not None and self.reason not in CONFIGURABLE_REASONS:
            raise ValidationError(f"Notifications for {self.reason} are not configurable")


@dataclass(frozen=True)
class Rule:
    enabled: bool
    scope: ObjectId | None = None
    event: str | None = None
    reason: NotificationReason | None = None
    channel: NotificationChannel | None = None


# What somebody gets before they ever open the settings screen, written as rules so
# that a default can be as precise as anything a user decides ("editors: the reuses
# but not the discussions"). They are read only where the user's own rules say nothing.
#
# Editors start silent: they are members of organizations whose datasets they have
# never touched, and mailing them every discussion of a 400-dataset organization is
# what this whole thing is meant to stop.
#
# Partial editors start loud, which only looks inconsistent: they are never given this
# reason unless the object was actually assigned to them, so "everything concerning
# me" is already a short list.
DEFAULT_RULES: list[Rule] = [
    Rule(reason=NotificationReason.OWNER, enabled=True),
    Rule(reason=NotificationReason.ORGANIZATION_ADMIN, enabled=True),
    Rule(reason=NotificationReason.ORGANIZATION_EDITOR, enabled=False),
    Rule(reason=NotificationReason.ORGANIZATION_PARTIAL_EDITOR, enabled=True),
    Rule(reason=NotificationReason.DISCUSSION_PARTICIPANT, enabled=True),
    Rule(reason=NotificationReason.EXPLICIT_SUBSCRIBER, enabled=True),
    Rule(channel=NotificationChannel.APP, enabled=True),
    Rule(channel=NotificationChannel.MAIL, enabled=True),
]


def rules_for(
    users: Iterable[User], events: Sequence[str], scopes: Sequence[Document]
) -> dict[ObjectId, list[Rule]]:
    """The rules of `users` that can apply to an event, by user id.

    One query for the whole event: resolving per recipient would multiply it by the
    size of an organization. Rows are read raw, since only identifiers are compared."""
    users = list(users)
    if not users:
        return {}

    rules: dict[ObjectId, list[Rule]] = {}
    for row in NotificationSetting.objects(
        Q(scope=None) | Q(scope__in=scopes),
        Q(event=None) | Q(event__in=events),
        user__in=users,
    ).as_pymongo():
        scope = row.get("scope")
        rules.setdefault(row["user"], []).append(
            Rule(
                scope=scope["_ref"].id if scope else None,
                event=row.get("event"),
                reason=NotificationReason(row["reason"]) if row.get("reason") else None,
                channel=NotificationChannel(row["channel"]) if row.get("channel") else None,
                enabled=row["enabled"],
            )
        )
    return rules


def resolve(
    rules: list[Rule],
    events: Sequence[str],
    scopes: Sequence[Document],
    reasons: Iterable[NotificationReason],
) -> set[NotificationChannel]:
    """The channels one recipient is reached through, given their rules.

    Two questions, in this order, for each reason the recipient has:

    1. Are they concerned at all? Only the rules without a channel answer it.
    2. If so, through which channels? Only the rules naming a channel answer it.

    Splitting them is what keeps following a thread from bringing back the mails one
    turned off: following says *whether*, a channel says *how*.

    Among the rules answering a question, the most specific wins: the subject first
    (a thread, then its dataset, then the organization, then everywhere), then the
    event (a single event, then its family, then every notification), then the reason
    (this reason, then whatever the reason). So a choice on a subject beats a choice on
    a reason, and a choice on an event beats a choice on a reason.

    The user's own rules are read first, and `DEFAULT_RULES` only where they say
    nothing: otherwise a precise default would beat a broad choice of the user.

    Reasons are then combined generously: being an administrator who muted their
    organizations does not silence the thread one took part in.
    """
    scope_rank = {scope_id: rank for rank, scope_id in enumerate([*(s.id for s in scopes), None])}
    event_rank = {event: rank for rank, event in enumerate([*events, None])}

    def most_specific(
        rules: list[Rule], reason: NotificationReason, channel: NotificationChannel | None
    ) -> bool | None:
        candidates = [
            rule
            for rule in rules
            if rule.channel == channel
            and rule.reason in (reason, None)
            and rule.scope in scope_rank
            and rule.event in event_rank
        ]
        if not candidates:
            return None
        best = min(
            candidates,
            key=lambda rule: (
                scope_rank[rule.scope],
                event_rank[rule.event],
                0 if rule.reason == reason else 1,
            ),
        )
        return best.enabled

    def decide(reason: NotificationReason, channel: NotificationChannel | None) -> bool:
        for layer in (rules, DEFAULT_RULES):
            enabled = most_specific(layer, reason, channel)
            if enabled is not None:
                return enabled
        return False

    return {
        channel
        for reason in reasons
        if decide(reason, None)
        for channel in NotificationChannel
        if decide(reason, channel)
    }


def subscribers_for(events: Sequence[str], scopes: Sequence[Document]) -> list[User]:
    """Users who chose to follow one of these subjects for this event.

    The other direction of the table: `rules_for` filters people the event already
    reaches, this one brings in those it would never have reached. Without it, somebody
    outside an organization could follow a subject and never hear about it.

    A rule without a subject is left out on purpose: "everywhere" means "everywhere I
    am already concerned", not "subscribe me to the whole site".
    """
    if not scopes:
        return []

    return list(
        NotificationSetting.objects(
            Q(event=None) | Q(event__in=events),
            scope__in=scopes,
            reason=None,
            channel=None,
            enabled=True,
        ).distinct("user")
    )


def resolved_for(user: User, subject: Document, event: str | None) -> dict:
    """Whether, why and where `user` hears about `event` on `subject`, the way the
    dispatch would decide it: so that a button shows the real state instead of
    guessing it from the rules it knows of."""
    # `events` builds on this module, hence the import at call time.
    from udata.core.discussions.models import Discussion
    from udata.features.notifications.events import (
        configurable_event_named,
        responsible_recipients,
        subject_scopes,
    )

    events = configurable_event_named(event).decision_events() if event else []
    scopes = subject_scopes(subject)
    recipients = (
        subject.owner_recipients()
        if isinstance(subject, Discussion)
        else responsible_recipients(subject)
    )
    reasons = {
        reason for recipient in recipients if recipient.key == user.id for reason in recipient.reasons
    }
    if NotificationSetting.objects(
        Q(event=None) | Q(event__in=events),
        user=user,
        scope__in=scopes,
        reason=None,
        channel=None,
        enabled=True,
    ).first():
        reasons.add(NotificationReason.EXPLICIT_SUBSCRIBER)

    rules = rules_for([user], events, scopes).get(user.id, [])
    return {
        "channels": sorted(resolve(rules, events, scopes, reasons)),
        "reasons": sorted(reasons),
    }


def visible_subject(scope, user: User):
    """The subject of a rule as its author may see it today, or `None`.

    A rule outlives the access to its subject: a dataset can turn private after one's
    departure from its organization, and its title must not leak through the list of
    what one follows."""
    from udata.core.discussions.models import Discussion

    subject = scope.subject if isinstance(scope, Discussion) else scope
    # Datasets and reuses say `deleted`, dataservices `deleted_at`.
    if getattr(subject, "deleted", None) or getattr(subject, "deleted_at", None):
        return None
    if getattr(subject, "private", False) and not user.sysadmin:
        organization = getattr(subject, "organization", None)
        if not (organization and organization.is_member(user)) and getattr(
            subject, "owner", None
        ) != user:
            return None
    return subject


@dataclass(frozen=True)
class SubjectSummary:
    """What the settings screen shows of the subject of a rule."""

    title: str
    page: str
    # What to group the subject under: its organization, or itself for an organization
    organization: Document | None


def subject_summary(setting: NotificationSetting) -> SubjectSummary | None:
    from udata.core.discussions.models import Discussion
    from udata.core.organization.models import Organization

    scope = setting.scope
    if scope is None:
        return None
    subject = visible_subject(scope, setting.user)
    if subject is None:
        return None
    return SubjectSummary(
        title=scope.title if isinstance(scope, Discussion) else str(subject),
        page=scope.self_web_url(),
        organization=subject
        if isinstance(subject, Organization)
        else getattr(subject, "organization", None),
    )
