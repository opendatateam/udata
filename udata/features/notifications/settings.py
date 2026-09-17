from collections.abc import Iterable, Sequence
from typing import Any

from mongoengine import CASCADE, Document, Q
from mongoengine.fields import BooleanField, EnumField, GenericReferenceField, ReferenceField

from udata.core.user.models import User
from udata.features.notifications.constants import (
    DEFAULT_ENABLED,
    NotificationCategory,
    NotificationChannel,
    NotificationReason,
)

# Everything a decision can be taken about. Anything an event can name in its
# `scopes()` belongs here, which is why a discussion sits next to the objects that
# carry them: muting a single thread is the finest useful grain.
NOTIFICATION_SCOPES = (
    "Organization",
    "Dataset",
    "Reuse",
    "Dataservice",
    "Post",
    "Topic",
    "Discussion",
)


class NotificationSetting(Document):
    """One decision a user took about one family of notifications, on one channel.

    Only decisions are stored, never the resolved grid: an administrator of a
    400-dataset organization would otherwise carry thousands of rows saying nothing,
    and no default could ever be changed again without migrating everybody.

    The decision is a plain yes or no. How often mails go out is a property of the
    person (`User.mail_cadence`), not of the subject.
    """

    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    # `None` means the decision covers every subject, and is the last word before the
    # defaults.
    scope = GenericReferenceField(choices=NOTIFICATION_SCOPES)
    category = EnumField(NotificationCategory, required=True)
    channel = EnumField(NotificationChannel, required=True)
    enabled = BooleanField(required=True)

    meta = {
        "indexes": [
            {"fields": ["user", "scope", "category", "channel"], "unique": True},
        ],
    }


def decisions_for(
    users: Iterable[User],
    category: NotificationCategory,
    scopes: Sequence[Document],
    channel: NotificationChannel,
) -> dict[Any, bool]:
    """What each of `users` decided about `category` on `channel`, by user id.

    `scopes` runs from the most specific subject to the broadest one, and the most
    specific decision wins. Users who never decided anything are absent from the
    result rather than mapped to a default, so the caller can tell "chose to be quiet"
    from "never said anything" — the two differ as soon as a default changes.

    One query for the whole event: resolving per recipient would multiply it by the
    size of an organization.
    """
    users = list(users)
    if not users:
        return {}

    scoped = Q(scope=None)
    for scope in scopes:
        scoped |= Q(scope=scope)

    by_user: dict[Any, dict[Any, bool]] = {}
    for setting in NotificationSetting.objects(
        scoped, user__in=users, category=category, channel=channel
    ):
        by_user.setdefault(setting.user.id, {})[setting.scope] = setting.enabled

    decisions = {}
    for user_id, choices in by_user.items():
        for scope in [*scopes, None]:
            if scope in choices:
                decisions[user_id] = choices[scope]
                break
    return decisions


def subscribers_for(category: NotificationCategory, scopes: Sequence[Document]) -> list[User]:
    """Users who asked to hear about `category` on one of these subjects.

    The other direction of the table: `decisions_for` filters people the event already
    reaches, this one brings in those it would never have reached. Without it, somebody
    outside an organization could store a setting that nothing would ever read.

    The global scope is deliberately left out. `scope=None` means "everywhere I am
    already concerned", not "subscribe me to the whole site".
    """
    if not scopes:
        return []

    scoped = Q(scope=scopes[0])
    for scope in scopes[1:]:
        scoped |= Q(scope=scope)

    return list(
        NotificationSetting.objects(scoped, category=category, enabled=True).distinct("user")
    )


def default_enabled(reasons: Iterable[NotificationReason], category: NotificationCategory) -> bool:
    """Whether somebody concerned for these reasons hears about this family by default.

    The most generous reason wins: being an editor who never opened a dataset does not
    cancel out having taken part in the discussion. This keeps the union of recipients
    the code produced before anybody could set anything.
    """
    return any(DEFAULT_ENABLED[reason, category] for reason in reasons)
