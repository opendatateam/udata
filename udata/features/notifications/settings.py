from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from bson import ObjectId
from flask_principal import Identity, RoleNeed, UserNeed
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
from udata.core.organization.models import Organization
from udata.core.organization.permissions import organization_needs
from udata.core.user.models import User
from udata.features.notifications.constants import FollowOrigin, NotificationReason
from udata.mongo.document import UDataDocument

# Everything a rule can be scoped to. Anything an event can name in its `scopes()`
# belongs here, which is why a discussion sits next to the objects that carry them:
# muting a single thread is the finest useful grain.
NOTIFICATION_SCOPES = ("Organization", "Discussion", *DISCUSSION_SUBJECTS)


@generate_fields()
class NotificationSetting(UDataDocument):
    """One rule a user set about their notifications.

    Every dimension is optional, and leaving one out means "whatever it is": no scope
    is everywhere, no event is every notification.

    - follow a thread: scope = the thread, event = `discussion`, yes
    - ignore a dataset: scope = the dataset, no
    - "no new reuses": event = `reuse.created`, no

    A notification reaches both the bell and the mailbox; only the cadence of the mails
    is the user's to choose.

    Why the user is concerned (their role, a thread they took part in) is not something
    they set: only the defaults tell reasons apart.

    Actions to take (an invitation, a source to validate) are the only notifications
    no rule applies to.

    See `resolve` for which rule wins when several apply.
    """

    # Not exposed: the API only ever lists and writes the current user's rules.
    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    # Read back as a bare `{class, id}`: a rule can name an object its author can no
    # longer see, and its title must not travel with it.
    scope = field(
        GenericReferenceField(choices=NOTIFICATION_SCOPES),
        nested_fields=api.model_reference,
        allow_null=True,
        description="The subject the rule is about, null for everywhere",
    )
    event = field(
        StringField(),
        description="A notification type, or a dotted prefix of some (`discussion` covers "
        "`discussion.*`), null for every notification",
    )
    enabled = field(BooleanField(required=True))
    # Only meaningful for a follow (a subject, yes): what made the
    # user follow, hence why they hear about it. Back to `FOLLOWED` as soon as the user
    # sets the rule themselves.
    origin = field(
        EnumField(FollowOrigin, default=FollowOrigin.FOLLOWED),
        readonly=True,
        description="What made the user follow the subject: by hand, by editing it, or by "
        "taking part in its discussions",
    )

    meta = {
        "indexes": [
            {"fields": ["user", "scope", "event"], "unique": True},
            # `follows` looks across every user, once per configurable event.
            ["scope", "event", "enabled"],
        ],
    }

    def clean(self):
        # `events` builds on this module, hence the import at call time.
        from udata.features.notifications.events import is_event_name

        super().clean()
        if self.event is not None and not is_event_name(self.event):
            raise ValidationError(f"{self.event} is not a notification type nor a prefix of one")


@dataclass(frozen=True)
class Rule:
    enabled: bool
    scope: ObjectId | None = None
    event: str | None = None


# What editors still hear about by default: rare, and about the organization as a whole
# rather than about datasets they never touched.
HEARD_BY_EDITORS = "organization.badge"


def heard_by_default(reason: NotificationReason, events: Sequence[str]) -> bool:
    """What somebody gets on the ground of `reason` before they ever open the settings
    screen, read only where their own rules say nothing.

    Every reason is heard, so that a new one cannot be silenced by forgetting it here,
    except editors: they are members of organizations whose datasets they have never
    touched, and mailing them every discussion of a 400-dataset organization is what
    this whole thing is meant to stop.

    Partial editors are heard, which only looks inconsistent: they are never given this
    reason unless the object was actually assigned to them, so "everything concerning
    me" is already a short list.
    """
    if reason == NotificationReason.ORGANIZATION_EDITOR:
        return HEARD_BY_EDITORS in events
    return True


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
        (Q(scope=None) | Q(scope__in=scopes)) & (Q(event=None) | Q(event__in=events)),
        user__in=users,
    ).as_pymongo():
        scope = row.get("scope")
        rules.setdefault(row["user"], []).append(
            Rule(
                scope=scope["_ref"].id if scope else None,
                event=row.get("event"),
                enabled=row["enabled"],
            )
        )
    return rules


def resolve(
    rules: list[Rule],
    events: Sequence[str],
    scopes: Sequence[Document],
    reasons: Iterable[NotificationReason],
) -> bool:
    """Whether one recipient hears about an event, given their rules.

    Among the rules that apply, the most specific wins: the subject first (a thread,
    then its dataset, then the organization, then everywhere), then the event (a single
    event, then its family, then every notification).

    The defaults (`heard_by_default`) are only read where the user's rules say nothing:
    otherwise a precise default would beat a broad choice of the user.

    Reasons are then combined generously: being an administrator who muted their
    organizations does not silence the thread one took part in.

    Taking part in a thread is following it: whether one hears about it as a participant
    is only decided by a rule on the thread itself or everywhere, never by one on its
    dataset or organization.
    """
    scope_rank = {scope_id: rank for rank, scope_id in enumerate([*(s.id for s in scopes), None])}
    event_rank = {event: rank for rank, event in enumerate([*events, None])}
    thread_ranks = {0, scope_rank[None]}

    def decide(reason: NotificationReason) -> bool:
        bound_to_thread = reason == NotificationReason.DISCUSSION_PARTICIPANT
        candidates = [
            rule
            for rule in rules
            if rule.scope in scope_rank
            and rule.event in event_rank
            and (not bound_to_thread or scope_rank[rule.scope] in thread_ranks)
        ]
        if not candidates:
            return heard_by_default(reason, events)
        best = min(candidates, key=lambda rule: (scope_rank[rule.scope], event_rank[rule.event]))
        return best.enabled

    return any(decide(reason) for reason in reasons)


# The reason a follow gives, depending on what made the user follow.
REASON_BY_ORIGIN = {
    FollowOrigin.FOLLOWED: NotificationReason.EXPLICIT_SUBSCRIBER,
    FollowOrigin.EDITED: NotificationReason.CONTRIBUTOR,
    FollowOrigin.DISCUSSED: NotificationReason.DISCUSSANT,
}


def follows(events: Sequence[str], scopes: Sequence[Document], **filters):
    """The follows of these subjects for this event: a subject, yes. A rule
    without a subject is left out on purpose: "everywhere" means "everywhere I am
    already concerned", not "subscribe me to the whole site"."""
    return NotificationSetting.objects(
        Q(event=None) | Q(event__in=events),
        scope__in=scopes,
        enabled=True,
        **filters,
    )


@dataclass(frozen=True)
class Resolution:
    """What `user` gets for one subject, echoed so that the caller can match each answer
    to its question."""

    scope: Document
    event: str | None
    heard: bool
    reasons: list[NotificationReason]


def resolved_for(
    user: User, subjects: Sequence[Document], event: str | None = None
) -> list[Resolution]:
    """Whether and why `user` hears about notifications on each subject (all of
    them without an event), the way the dispatch would decide it, so that the front
    never resolves rules by itself.

    Several subjects at once, so that a page asks once for all of its threads; the rules
    are loaded once for all of them. A subject is required: without one, nothing reaches
    anybody (a rule naming no subject follows nothing).
    """
    # `events` builds on this module, hence the import at call time.
    from udata.core.discussions.models import Discussion
    from udata.features.notifications.events import (
        event_chain,
        responsible_recipients,
        subject_scopes,
    )

    chain = event_chain(event)
    scopes_of = [(subject, subject_scopes(subject)) for subject in subjects]
    rules = rules_for(
        [user],
        chain,
        list({scope.pk: scope for _, scopes in scopes_of for scope in scopes}.values()),
    ).get(user.id, [])

    resolutions = []
    for subject, scopes in scopes_of:
        recipients = (
            subject.owner_recipients()
            if isinstance(subject, Discussion)
            else responsible_recipients(subject)
        )
        held = {
            reason
            for recipient in recipients
            if recipient.key == user.id
            for reason in recipient.reasons
        } | {
            REASON_BY_ORIGIN[setting.origin]
            for setting in follows(chain, scopes, user=user).only("origin")
        }
        resolutions.append(
            Resolution(
                scope=subject,
                event=event,
                heard=not user.notifications_paused and resolve(rules, chain, scopes, held),
                reasons=sorted(held),
            )
        )
    return resolutions


def visible_subject(scope):
    """The subject of a rule as the current user may see it today, or `None`.

    A rule outlives the access to its subject: a dataset can turn private after one's
    departure from its organization, and its title must not leak through the list of
    what one follows. Each kind of subject says who may read it through its `read`
    permission; one without any (an organization, a topic) is public."""
    from udata.core.discussions.models import Discussion

    subject = scope.subject if isinstance(scope, Discussion) else scope
    read = getattr(subject, "permissions", {}).get("read")
    return subject if read is None or read.can() else None


def readable_by(user: User, scope) -> bool:
    """Whether `user` may read the subject of `scope`, as its `read` permission says.

    A follow reaches people the event would not reach by itself, and anybody can follow
    an organization: without this, its private datasets would leak through their
    discussions. The permission is checked against the needs `user` would have once
    logged in, not against `current_user`, who is whoever triggered the event."""
    from udata.core.discussions.models import Discussion

    subject = scope.subject if isinstance(scope, Discussion) else scope
    read = getattr(subject, "permissions", {}).get("read")
    if read is None:
        return True
    identity = Identity(user.id)
    identity.provides.add(UserNeed(user.fs_uniquifier))
    identity.provides.update(RoleNeed(role.name) for role in user.roles)
    identity.provides.update(organization_needs(user))
    return read.allows(identity)


@dataclass(frozen=True)
class SubjectSummary:
    """What the settings screen shows of the subject of a rule."""

    title: str
    page: str
    # What to group the subject under: its organization, or itself for an organization
    organization: Document | None


def subject_summary(setting: NotificationSetting) -> SubjectSummary | None:
    from udata.core.discussions.models import Discussion

    scope = setting.scope
    if scope is None:
        return None
    subject = visible_subject(scope)
    if subject is None:
        return None
    return SubjectSummary(
        title=scope.title if isinstance(scope, Discussion) else str(subject),
        page=scope.self_web_url(),
        organization=subject
        if isinstance(subject, Organization)
        else getattr(subject, "organization", None),
    )
