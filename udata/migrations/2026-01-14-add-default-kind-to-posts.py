"""
This migration sets Post.kind to "news" for posts that don't have a kind.
This is necessary because the default value is only applied to new documents,
not existing ones.
"""

import logging

from udata.models import Post

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing posts without kind...")
    count = Post.objects(kind__exists=False).update(kind="news")
    log.info(f"\tSet kind='news' for {count} posts")
