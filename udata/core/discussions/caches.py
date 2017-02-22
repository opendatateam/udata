# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.app import cache

from .signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed,
    on_discussion_deleted
)


@on_new_discussion.connect
@on_new_discussion_comment.connect
@on_discussion_closed.connect
@on_discussion_deleted.connect
def invalidate_discussions_cache(discussion, **kwargs):
    cache_key = 'discussions{url}?for={id}'.format(
        url=url_for('api.discussions'), id=discussion.subject.id)
    cache.delete(cache_key)
