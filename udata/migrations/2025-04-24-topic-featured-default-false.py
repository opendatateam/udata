"""
This migration updates Topic.featured to False when it is None.
"""

import logging

from udata.models import Topic

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing topics...")
    count = Topic.objects(featured__exists=False).update(featured=False)
    log.info(f"\tConverted {count} topics from `featured=None` to `featured=False`")
