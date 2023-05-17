from datetime import datetime

from udata.models import db
from .signals import on_follow, on_unfollow


__all__ = ('Follow', )


class FollowQuerySet(db.BaseQuerySet):
    def following(self, user):
        return self(follower=user, until=None)

    def followers(self, user):
        return self(following=user, until=None)

    def is_following(self, user, following):
        return self(follower=user, following=following, until=None).count() > 0


class Follow(db.Document):
    follower = db.ReferenceField('User', required=True)
    following = db.GenericReferenceField()
    since = db.DateTimeField(required=True, default=datetime.utcnow)
    until = db.DateTimeField()

    meta = {
        'indexes': [
            'follower',
            'following',
            ('follower', 'until'),
            ('following', 'until'),
        ],
        'queryset_class': FollowQuerySet,
    }


@db.post_save.connect
def emit_new_follower(sender, document, **kwargs):
    if isinstance(document, Follow):
        if document.until:
            on_unfollow.send(document)
        else:
            on_follow.send(document)
