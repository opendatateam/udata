import datetime

from udata.core.organization.constants import PRODUCER_TYPES
from udata.core.organization.helpers import get_producer_type
from udata.core.topic.models import Topic
from udata.search import (
    BoolFilter,
    Filter,
    ListFilter,
    ModelSearchAdapter,
    register,
)
from udata.utils import to_iso_datetime
from udata_search_service.consumers import TopicConsumer
from udata_search_service.services import TopicService

__all__ = ("TopicSearch",)


@register
class TopicSearch(ModelSearchAdapter):
    model = Topic
    service_class = TopicService
    consumer_class = TopicConsumer

    sorts = {
        "name": "name",
        "created": "created_at",
        "last_modified": "last_modified",
    }

    filters = {
        "tag": ListFilter(),
        "featured": BoolFilter(),
        "last_update_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
        "organization": Filter(),
        "producer_type": Filter(choices=list(PRODUCER_TYPES)),
    }

    @classmethod
    def is_indexable(cls, topic: Topic) -> bool:
        return True

    @classmethod
    def mongo_search(cls, args):
        """
        Fallback Mongo search when ELASTICSEARCH_URL is not configured.
        We mimic the existing TopicsAPI behaviour as much as possible.
        """
        from flask_security import current_user
        from mongoengine import Q

        from udata.core.topic.parsers import TopicApiParser

        topics = Topic.objects.visible_by_user(current_user, Q(private__ne=True))
        parser = TopicApiParser()
        topics = parser.parse_filters(topics, args)

        sort = (
            cls.parse_sort(args["sort"]) or ("$text_score" if args["q"] else None) or "-created_at"
        )
        return topics.order_by(sort).paginate(args["page"], args["page_size"])

    @classmethod
    def serialize(cls, topic: Topic) -> dict:
        """
        Serialize a Topic into a flat document suitable for the search-service.
        """
        return {
            "id": str(topic.id),
            "name": topic.name,
            "description": topic.description or "",
            "tags": topic.tags or [],
            "featured": bool(topic.featured),
            "private": bool(topic.private),
            "created_at": to_iso_datetime(topic.created_at)
            if isinstance(topic.created_at, (datetime.datetime, datetime.date))
            else None,
            "last_modified": to_iso_datetime(topic.last_modified)
            if hasattr(topic, "last_modified")
            and isinstance(topic.last_modified, (datetime.datetime, datetime.date))
            else None,
            "organization": str(topic.organization.id) if topic.organization else None,
            "organization_name": topic.organization.name if topic.organization else None,
            "producer_type": get_producer_type(topic),
        }
