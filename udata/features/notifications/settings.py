from collections.abc import Iterable, Sequence

from bson import ObjectId
from mongoengine import CASCADE, Document, ValidationError
from mongoengine.fields import (
    BooleanField,
    EnumField,
    GenericReferenceField,
    ListField,
    ReferenceField,
    StringField,
)

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.core.discussions.constants import DISCUSSION_SUBJECTS
from udata.core.user.models import User
from udata.features.notifications.constants import (
    DEFAULT_ENABLED,
    NotificationChannel,
    NotificationReason,
)
from udata.mongo.document import UDataDocument

# Everything a decision can be taken about. Anything an event can name in its
# `scopes()` belongs here, which is why a discussion sits next to the objects that
# carry them: muting a single thread is the finest useful grain.
NOTIFICATION_SCOPES = ("Organization", "Discussion", *DISCUSSION_SUBJECTS)

# Only reached by actions to take, which are not configurable: a preference about it
# would be stored and never read.
CONFIGURABLE_REASONS = tuple(
    reason for reason in NotificationReason if reason is not NotificationReason.SYSADMIN
)


@generate_fields()
class NotificationSetting(UDataDocument):
    """What a user decided about one subject: follow it, or ignore it.

    Following makes the user concerned as an explicit subscriber, ignoring silences the
    subject whatever the reasons the user had to hear about it. How the user is then
    reached is not decided here but by their `NotificationPreference`s: a decision about
    a subject says *whether*, never *how*.

    Only decisions are stored, never the resolved grid: an administrator of a
    400-dataset organization would otherwise carry thousands of rows saying nothing.
    """

    # Not exposed: the API only ever lists and writes the current user's decisions.
    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    # Read back as a bare `{class, id}`: a decision can name an object its author can no
    # longer see, and its title must not travel with it.
    scope = field(
        GenericReferenceField(choices=NOTIFICATION_SCOPES, required=True),
        nested_fields=api.model_reference,
    )
    # The name of a `ConfigurableEvent` class: a single event (`NewDiscussionComment`),
    # a family of them (`DiscussionEvent`), or all of them (`ConfigurableEvent`). The
    # narrower one wins on a given subject.
    event = field(
        StringField(required=True),
        description="A configurable event class: a single event, its family, or ConfigurableEvent for all",
    )
    enabled = field(BooleanField(required=True))

    meta = {
        "indexes": [
            {"fields": ["user", "scope", "event"], "unique": True},
            # `subscribers_for` looks across every user, once per configurable event.
            ["scope", "event", "enabled"],
        ],
    }

    def clean(self):
        # `events` builds on this module, hence the import at call time.
        from udata.features.notifications.events import settable_events

        super().clean()
        if self.event not in settable_events():
            raise ValidationError(f"{self.event} is not a configurable notification")


@generate_fields()
class NotificationPreference(UDataDocument):
    """How a user wants to hear about what concerns them for one reason.

    "My own datasets in the bell and by mail, the organizations I edit nowhere": the
    reason is what a user recognizes when deciding, and what the mail footer names.
    Only stored once the user departs from `DEFAULT_ENABLED`.
    """

    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    reason = field(EnumField(NotificationReason, required=True))
    channels = field(ListField(EnumField(NotificationChannel)))

    meta = {
        "indexes": [
            {"fields": ["user", "reason"], "unique": True},
        ],
    }

    def clean(self):
        super().clean()
        if self.reason not in CONFIGURABLE_REASONS:
            raise ValidationError(f"Notifications for {self.reason} are not configurable")


def visible_subject(scope, user: User):
    """The subject of a decision as its author may see it today, or `None`.

    A decision outlives the access to its subject: a dataset can turn private after
    one's departure from its organization, and its title must not leak through the
    list of what one follows."""
    from udata.core.discussions.models import Discussion

    subject = scope.subject if isinstance(scope, Discussion) else scope
    if getattr(subject, "deleted", None) or getattr(subject, "deleted_at", None):
        return None
    if getattr(subject, "private", False):
        organization = getattr(subject, "organization", None)
        if not (organization and organization.is_member(user)) and getattr(subject, "owner", None) != user:
            return None
    return subject


def subject_summary(setting: "NotificationSetting") -> dict | None:
    """What the settings screen shows of a followed or ignored subject: a title, a link,
    and the organization to group it under."""
    from udata.core.discussions.models import Discussion
    from udata.core.organization.models import Organization

    scope = setting.scope
    subject = visible_subject(scope, setting.user)
    if subject is None:
        return None
    return {
        "title": scope.title if isinstance(scope, Discussion) else str(subject),
        "page": scope.self_web_url(),
        "organization": subject if isinstance(subject, Organization) else getattr(subject, "organization", None),
    }


def default_channels(reason: NotificationReason) -> set[NotificationChannel]:
    return set(NotificationChannel) if DEFAULT_ENABLED[reason] else set()


def preferences_for(
    users: Iterable[User],
) -> dict[tuple[ObjectId, NotificationReason], set[NotificationChannel]]:
    """The channels each of `users` chose per reason, for the reasons they changed.

    One query for the whole event: resolving per recipient would multiply it by the
    size of an organization."""
    users = list(users)
    if not users:
        return {}
    return {
        (preference["user"], NotificationReason(preference["reason"])): {
            NotificationChannel(channel) for channel in preference.get("channels", [])
        }
        for preference in NotificationPreference.objects(user__in=users).as_pymongo()
    }


def resolved_preferences(user: User) -> list[dict]:
    """Every configurable reason with the channels it reaches the user through, defaults
    included: what the settings screen shows."""
    chosen = preferences_for([user])
    return [
        {
            "reason": reason,
            "channels": sorted(chosen.get((user.id, reason), default_channels(reason))),
        }
        for reason in CONFIGURABLE_REASONS
    ]


def decisions_for(
    users: Iterable[User],
    events: Sequence[str],
    scopes: Sequence[Document],
) -> dict[ObjectId, bool]:
    """What each of `users` decided about an event on these subjects, by user id.

    `events` names the event from its own class up to `ConfigurableEvent`, and `scopes`
    runs from the most specific subject to the broadest one. The subject is weighed
    first: ignoring one thread holds against following its whole dataset. Only then
    does the narrower event win on that subject.

    Users who decided nothing are absent from the result, so the caller falls back on
    their reasons.
    """
    users = list(users)
    if not users or not scopes:
        return {}

    by_user: dict[ObjectId, dict[tuple[ObjectId, str], bool]] = {}
    for setting in NotificationSetting.objects(
        user__in=users, scope__in=scopes, event__in=events
    ).as_pymongo():
        choice = (setting["scope"]["_ref"].id, setting["event"])
        by_user.setdefault(setting["user"], {})[choice] = setting["enabled"]

    precedence = [(scope.id, event) for scope in scopes for event in events]
    decisions = {}
    for user, choices in by_user.items():
        for choice in precedence:
            if choice in choices:
                decisions[user] = choices[choice]
                break
    return decisions


def subscribers_for(events: Sequence[str], scopes: Sequence[Document]) -> list[User]:
    """Users who chose to follow one of these subjects for this event.

    The other direction of the table: `decisions_for` filters people the event already
    reaches, this one brings in those it would never have reached. Without it, somebody
    outside an organization could follow a subject and never hear about it.
    """
    if not scopes:
        return []

    return list(
        NotificationSetting.objects(scope__in=scopes, event__in=events, enabled=True).distinct(
            "user"
        )
    )
