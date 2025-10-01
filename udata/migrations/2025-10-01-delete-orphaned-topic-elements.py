"""
Delete TopicElements that are not associated with an existing Topic
"""

import logging

import mongoengine

from udata.core.topic.models import TopicElement

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing orphaned TopicElements...")

    topic_elements = TopicElement.objects.no_cache().all()
    deleted_count = 0

    for element in topic_elements:
        try:
            # Try to access the topic - will raise DoesNotExist if topic was deleted
            if element.topic:
                _ = element.topic.id
        except mongoengine.errors.DoesNotExist:
            # Topic doesn't exist, delete the orphaned element
            element.delete()
            deleted_count += 1

    log.info(f"Deleted {deleted_count} orphaned TopicElements")
