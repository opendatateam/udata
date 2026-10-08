"""What a user gets on some subjects, and following them or not: the questions the
settings screens ask, answered from the rules (`settings`) and from who each event
reaches (`events`)."""

from collections.abc import Sequence
from dataclasses import dataclass

from mongoengine import Document, Q

from udata.core.discussions.models import Discussion
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.constants import (
    TYPES_REQUIRING_ACTION,
    NotificationReason,
    NotificationType,
    event_chain,
)
from udata.features.notifications.events import (
    discussion_recipients,
    event_for_type,
    responsible_recipients,
    subject_scopes,
)
from udata.features.notifications.settings import (
    REASON_BY_ORIGIN,
    NotificationSetting,
    SubjectSummary,
    readable_by,
    resolve,
    rules_for,
    set_rule,
    subject_summary,
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

    @property
    def subject(self) -> SubjectSummary | None:
        return subject_summary(self.scope)


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

    The dispatch decides type by type, and so does this: a family of events, or every
    notification, is heard when one of its types is. Asked as a whole, "every
    notification" would miss what the defaults only grant to some types, the badges of
    an editor.
    """
    types = [
        type
        for type in NotificationType
        if type not in TYPES_REQUIRING_ACTION
        and (event is None or type == event or type.startswith(f"{event}."))
    ]
    scopes_of = [(subject, subject_scopes(subject)) for subject in subjects]
    rules = rules_for(
        [user],
        list({name for type in types for name in event_chain(type)}),
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
        roles = {
            reason
            for recipient in recipients
            if recipient.key == user.id
            for reason in recipient.reasons
        }
        # As at dispatch: a follow only brings what its user may read.
        followed = (
            {
                REASON_BY_ORIGIN[rule.origin]
                for rule in rules
                if rule.enabled and rule.scope in scope_ids
            }
            if readable_by(user, subject)
            else set()
        )

        def held_for(type: NotificationType) -> set[NotificationReason]:
            held = set(roles)
            # On the organization, a partial editor is only concerned by what is about the
            # organization itself: the rest reaches them through what was assigned.
            if isinstance(subject, Organization) and not type.startswith("organization."):
                held.discard(NotificationReason.ORGANIZATION_PARTIAL_EDITOR)
            if event_for_type(type).reaches_subscribers:
                held |= followed
            return held

        resolutions.append(
            Resolution(
                scope=subject,
                event=event,
                heard=any(
                    resolve(rules, event_chain(type), scopes, held_for(type)) for type in types
                ),
                reasons=sorted(roles | followed),
                muted=own.get((subject.pk, event)) is False,
                followed_events=sorted(
                    named
                    for (scope_id, named), enabled in own.items()
                    if scope_id == subject.pk and enabled and named and named.startswith(under)
                ),
            )
        )
    return resolutions


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
