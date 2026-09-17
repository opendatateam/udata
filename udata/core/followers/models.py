from datetime import UTC, datetime

from mongoengine.fields import DateTimeField, GenericReferenceField, ReferenceField
from mongoengine.signals import post_save

from udata.api_fields import field, generate_fields
from udata.core.user.models import User
from udata.mongo.document import UDataDocument as Document
from udata.mongo.queryset import UDataQuerySet

from .signals import on_follow, on_unfollow

__all__ = ("Follow",)


class FollowQuerySet(UDataQuerySet):
    def following(self, user):
        return self(follower=user, until=None)

    def followers(self, user):
        return self(following=user, until=None)

    def is_following(self, user, following):
        return self(follower=user, following=following, until=None).count() > 0


@generate_fields()
class Follow(Document[FollowQuerySet]):
    # Read only: a follow is created and ended through the dedicated POST and DELETE,
    # which take no body.
    follower = field(
        ReferenceField(User, required=True),
        readonly=True,
        filterable={
            "key": "user",
            "help": "Filter follower by user, it allows to check if a user is following the object",
        },
        description="The follower",
    )
    # `following` and `until` stay out of the API: the endpoint is always scoped to one
    # followed object, and an ended follow is never listed.
    following = GenericReferenceField()
    since = field(
        DateTimeField(required=True, default=lambda: datetime.now(UTC)),
        readonly=True,
        description="The date from which the user started following",
    )
    until = DateTimeField()

    meta = {
        "indexes": [
            "follower",
            "following",
            ("follower", "until"),
            ("following", "until"),
        ],
        "queryset_class": FollowQuerySet,
    }


@post_save.connect
def emit_new_follower(sender, document, **kwargs):
    if isinstance(document, Follow):
        if document.until:
            on_unfollow.send(document)
        else:
            on_follow.send(document)
