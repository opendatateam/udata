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
from udata.core.discussions.models import Discussion
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

    Following a subject here is not putting it in one's favorites (`Follow`), as watching
    a repository is not starring it. Following is a private setting: hearing about the
    life of a subject one looks after, its discussions, its reuses. A favorite is a
    public signal, counted and shown on the subject: if it is to bring notifications, it
    is by making its owner a recipient of the few events a reader cares about (a new
    resource), with a reason of its own, not by creating a follow here.

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
    # Only meaningful for a follow, that is a "yes" on a subject: what made the user
    # follow it, hence why they hear about it. Back to `FOLLOWED` as soon as the user sets
    # the rule themselves.
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
    origin: FollowOrigin = FollowOrigin.FOLLOWED


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
                origin=FollowOrigin(row.get("origin", FollowOrigin.FOLLOWED)),
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

    Among the rules that apply, a rule beats another when it is at least as specific on
    both of their dimensions: the subject (a thread, then its dataset, then the
    organization, then everywhere) and the event (a single event, then its family, then
    every notification). Ignoring a dataset but following one of its threads, or ignoring
    the discussions of a dataset but keeping their answers, is therefore unambiguous.

    Two rules each more specific on one dimension are two deliberate choices that
    contradict each other: following a dataset, and turning off a type of notification
    anywhere; following the answers on a dataset, and ignoring one of its threads. The
    "no" wins: a way out offered to the user has to hold, whatever they follow.

    A follow udata made by itself, for editing a subject or taking part in its
    discussions, was never chosen: any "no" that applies beats it, however broad. Muting
    an organization then also mutes the datasets of it one edited, which a follow set by
    hand would keep.

    The defaults (`heard_by_default`) are only read where the user's rules say nothing:
    otherwise a precise default would beat a broad choice of the user.

    Reasons are then combined generously: being an administrator who muted their
    organizations does not silence the thread one took part in.

    Taking part in a thread is following it: whether one hears about it as a participant
    is decided by a rule on the thread, on what it is about, or everywhere, never by one
    on the organization behind it ("only what I follow" there keeps the threads one
    answered).
    """
    scope_rank = {scope_id: rank for rank, scope_id in enumerate([*(s.id for s in scopes), None])}
    event_rank = {event: rank for rank, event in enumerate([*events, None])}
    # The thread, what it is about, and everywhere.
    thread_ranks = {0, 1, scope_rank[None]}

    def ranks(rule: Rule) -> tuple[int, int]:
        return scope_rank[rule.scope], event_rank[rule.event]

    def beats(rule: Rule, other: Rule) -> bool:
        return all(mine <= theirs for mine, theirs in zip(ranks(rule), ranks(other)))

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
        if any(not rule.enabled for rule in candidates):
            candidates = [
                rule
                for rule in candidates
                if not rule.enabled or rule.origin == FollowOrigin.FOLLOWED
            ]
        unbeaten = [
            rule
            for rule in candidates
            if not any(other is not rule and beats(other, rule) for other in candidates)
        ]
        return all(rule.enabled for rule in unbeaten)

    return any(decide(reason) for reason in reasons)


# The reason a follow gives, depending on what made the user follow.
REASON_BY_ORIGIN = {
    FollowOrigin.FOLLOWED: NotificationReason.EXPLICIT_SUBSCRIBER,
    FollowOrigin.EDITED: NotificationReason.CONTRIBUTOR,
    FollowOrigin.DISCUSSED: NotificationReason.DISCUSSANT,
}


def follows(events: Sequence[str], scopes: Sequence[Document]):
    """The follows of these subjects for this event: a subject, yes. A rule
    without a subject is left out on purpose: "everywhere" means "everywhere I am
    already concerned", not "subscribe me to the whole site"."""
    return NotificationSetting.objects(
        Q(event=None) | Q(event__in=events),
        scope__in=scopes,
        enabled=True,
    )


@dataclass(frozen=True)
class Resolution:
    """What `user` gets for one subject, echoed so that the caller can match each answer
    to its question."""

    scope: Document
    event: str | None
    heard: bool
    reasons: list[NotificationReason]
    # The user said no to exactly this subject and event.
    muted: bool
    # The narrower events the user still follows on exactly this subject: hearing about
    # some of its notifications only reads as `heard` when asking about each of them.
    followed_events: list[str]


def resolved_for(
    user: User, subjects: Sequence[Document], event: str | None = None
) -> list[Resolution]:
    """Whether and why `user` hears about notifications on each subject (all of
    them without an event), the way the dispatch would decide it, so that the front
    never resolves rules by itself.

    Several subjects at once, so that a page asks once for all of its threads; the rules
    are loaded once for all of them. A subject is required: without one, nothing reaches
    anybody (a rule naming no subject follows nothing).

    The pause is left out: it holds everything back whatever the rules say, and is
    shown as such. Following or not is still worth showing, and changing, meanwhile.
    """
    # `events` builds on this module, hence the import at call time.
    from udata.features.notifications.events import (
        discussion_recipients,
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
    own = {
        (row["scope"]["_ref"].id, row.get("event")): row["enabled"]
        for row in NotificationSetting.objects(user=user, scope__in=list(subjects)).as_pymongo()
    }
    under = f"{event}." if event else ""

    resolutions = []
    for subject, scopes in scopes_of:
        recipients = (
            discussion_recipients(subject)
            if isinstance(subject, Discussion)
            else responsible_recipients(subject)
        )
        scope_ids = {scope.id for scope in scopes}
        held = {
            reason
            for recipient in recipients
            if recipient.key == user.id
            for reason in recipient.reasons
        }
        # As at dispatch: a follow only brings what its user may read.
        if readable_by(user, subject):
            held |= {
                REASON_BY_ORIGIN[rule.origin]
                for rule in rules
                if rule.enabled and rule.scope in scope_ids
            }
        resolutions.append(
            Resolution(
                scope=subject,
                event=event,
                heard=resolve(rules, chain, scopes, held),
                reasons=sorted(held),
                muted=own.get((subject.pk, event)) is False,
                followed_events=sorted(
                    named
                    for (scope_id, named), enabled in own.items()
                    if scope_id == subject.pk and enabled and named and named.startswith(under)
                ),
            )
        )
    return resolutions


def set_rule(
    user: User, scope: Document | None, event: str | None, enabled: bool | None
) -> tuple[NotificationSetting | None, bool]:
    """Set a rule as the user decided it, or withdraw it with `None`, and return it with
    whether it was created.

    A follow udata made by itself, for editing the subject or taking part in its
    discussions, is turned into a "no" rather than withdrawn: withdrawn, the next edit
    or answer would make it again."""
    key = {"user": user, "scope": scope, "event": event}
    if enabled is None:
        existing = NotificationSetting.objects(**key).first()
        if existing is None:
            return None, False
        if not existing.enabled or existing.origin == FollowOrigin.FOLLOWED:
            existing.delete()
            return None, False
        enabled = False
    return NotificationSetting.objects.get_or_create(
        **key, updates={"enabled": enabled, "origin": FollowOrigin.FOLLOWED}
    )


def set_follow(user: User, subject: Document, event: str | None, followed: bool) -> Resolution:
    """Follow some notifications on a subject (all of them without an event), or stop,
    and say what the user gets once done.

    Following is a "concerned" rule. Stopping withdraws the user's own follow first: if
    nothing else brings these notifications, that is enough, and the defaults of their
    role stay untouched. Only when a role or a broader follow still brings them is "not
    concerned" written.

    Either way, the rules on narrower events of the same subject go: left behind, a
    narrower "no" would beat the follow, and a narrower follow the "no".
    """
    narrower = Q(event__ne=None) if event is None else Q(event__startswith=f"{event}.")
    NotificationSetting.objects(narrower, user=user, scope=subject).delete()

    if followed:
        set_rule(user, subject, event, True)
        return resolved_for(user, [subject], event)[0]

    own = NotificationSetting.objects(user=user, scope=subject, event=event).first()
    if own is not None and own.enabled:
        set_rule(user, subject, event, None)
    [resolution] = resolved_for(user, [subject], event)
    if not resolution.heard:
        return resolution
    set_rule(user, subject, event, False)
    return resolved_for(user, [subject], event)[0]


def read_permission(scope):
    """What a rule on `scope` is about, a thread standing for its subject, and who may
    read it: its `read` permission, `None` when anybody may (an organization, a topic)."""
    subject = scope.subject if isinstance(scope, Discussion) else scope
    return subject, getattr(subject, "permissions", {}).get("read")


def readable_by(user: User, scope) -> bool:
    """Whether `user` may read the subject of `scope`, as its `read` permission says.

    A follow reaches people the event would not reach by itself, and anybody can follow
    an organization: without this, its private datasets would leak through their
    discussions. The permission is checked against the needs `user` would have once
    logged in, not against `current_user`, who is whoever triggered the event."""
    _, read = read_permission(scope)
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
    # The organization the subject belongs to, none for an organization itself
    organization: Document | None


def subject_summary(setting: NotificationSetting) -> SubjectSummary | None:
    """A rule outlives the access to its subject: a dataset can turn private after one's
    departure from its organization, and its title must not leak through the list of
    what one follows."""
    scope = setting.scope
    if scope is None:
        return None
    subject, read = read_permission(scope)
    if read is not None and not read.can():
        return None
    return SubjectSummary(
        title=scope.title if isinstance(scope, Discussion) else str(subject),
        page=scope.self_web_url(),
        organization=getattr(subject, "organization", None),
    )
