from datetime import datetime

from mongoengine.fields import DateTimeField, GenericReferenceField, ReferenceField
from mongoengine.signals import post_save

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


class Follow(Document):
    follower = ReferenceField("User", required=True)
    following = GenericReferenceField()
    since = DateTimeField(required=True, default=datetime.utcnow)
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
