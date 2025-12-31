import datetime

from udata.core.organization.constants import PRODUCER_TYPES, get_producer_type
from udata.core.topic.models import Topic
from udata.models import Organization, User
from udata.search import (
    BoolFilter,
    Filter,
    ListFilter,
    ModelSearchAdapter,
    register,
)
from udata.utils import to_iso_datetime

__all__ = ("TopicSearch",)


@register
class TopicSearch(ModelSearchAdapter):
    model = Topic
    search_url = "topics/"

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
        Fallback Mongo search when SEARCH_SERVICE_API_URL is not configured.
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
        from udata.core.topic.models import TopicElement

        organization_id = None
        organization_name = None
        org = None
        owner = None

        if topic.organization:
            org = Organization.objects(id=topic.organization.id).first()
            organization_id = str(org.id)
            organization_name = org.name
        elif topic.owner:
            owner = User.objects(id=topic.owner.id).first()

        nb_datasets = TopicElement.objects(topic=topic, __raw__={"element._cls": "Dataset"}).count()
        nb_reuses = TopicElement.objects(topic=topic, __raw__={"element._cls": "Reuse"}).count()
        nb_dataservices = TopicElement.objects(
            topic=topic, __raw__={"element._cls": "Dataservice"}
        ).count()

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
            "organization": organization_id,
            "organization_name": organization_name,
            "producer_type": get_producer_type(org, owner),
            "nb_datasets": nb_datasets,
            "nb_reuses": nb_reuses,
            "nb_dataservices": nb_dataservices,
        }
