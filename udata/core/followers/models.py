# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from blinker import Signal

from udata.models import db


__all__ = ('Follow', 'FollowOrg', 'FollowDataset')


class FollowQuerySet(db.BaseQuerySet):
    def following(self, user):
        return self(follower=user, until=None)

    def followers(self, user):
        return self(following=user, until=None)

    def is_following(self, user, following):
        return self(follower=user, following=following, until=None).count() > 0


class Follow(db.Document):
    follower = db.ReferenceField('User')
    following = db.ReferenceField('User')
    since = db.DateTimeField(required=True, default=datetime.now)
    until = db.DateTimeField()

    on_new = Signal()

    meta = {
        'indexes': [
            'follower',
            'following',
            ('follower', 'until'),
            ('following', 'until'),
        ],
        'queryset_class': FollowQuerySet,
        'allow_inheritance': True,
    }


class FollowOrg(Follow):
    following = db.ReferenceField('Organization')


class FollowDataset(Follow):
    following = db.ReferenceField('Dataset')


@db.post_save.connect_via(Follow)
def emit_new_follower(sender, document, **kwargs):
    document.on_new.send(document)


@db.post_save.connect_via(FollowOrg)
def emit_new_org_follower(sender, document, **kwargs):
    document.on_new.send(document)


@db.post_save.connect_via(FollowDataset)
def emit_new_dataset_follower(sender, document, **kwargs):
    document.on_new.send(document)
