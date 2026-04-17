import datetime

from udata.core.organization.constants import PRODUCER_TYPES
from udata.core.organization.helpers import get_producer_type
from udata.core.reuse.api import DEFAULT_SORTING, ReuseApiParser
from udata.core.topic.models import TopicElement
from udata.models import Organization, Reuse, User
from udata.search import (
    BoolFilter,
    Filter,
    ListFilter,
    ModelSearchAdapter,
    ModelTermsFilter,
    register,
)
from udata.utils import to_iso_datetime
from udata_search_service.consumers import ReuseConsumer
from udata_search_service.services import ReuseService

__all__ = ("ReuseSearch",)


@register
class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    service_class = ReuseService
    consumer_class = ReuseConsumer

    sorts = {
        "created": "created_at",
        "datasets": "metrics.datasets",
        "followers": "metrics.followers",
        "views": "metrics.views",
    }

    # Uses __badges__ (not available_badges) so that users can still filter
    # by any existing badge, even hidden ones.
    filters = {
        "tag": ListFilter(),
        "organization": ModelTermsFilter(model=Organization),
        "organization_badge": Filter(choices=list(Organization.__badges__)),
        "owner": ModelTermsFilter(model=User),
        "type": Filter(),
        "badge": Filter(choices=list(Reuse.__badges__)),
        "featured": BoolFilter(),
        "topic": Filter(),
        "archived": BoolFilter(),
        "producer_type": Filter(choices=list(PRODUCER_TYPES)),
        "last_update_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
    }

    @classmethod
    def is_indexable(cls, reuse: Reuse) -> bool:
        return reuse.is_visible

    @classmethod
    def mongo_search(cls, args):
        reuses = Reuse.objects.visible()
        reuses = ReuseApiParser.parse_filters(reuses, args)

        sort = (
            cls.parse_sort(args["sort"])
            or ("$text_score" if args["q"] else None)
            or DEFAULT_SORTING
        )
        return reuses.order_by(sort).paginate(args["page"], args["page_size"])

    @classmethod
    def serialize(cls, reuse: Reuse) -> dict:
        organization = None

        topic_object_ids = list(
            set(te.topic.id for te in TopicElement.objects(element=reuse) if te.topic)
        )

        if reuse.organization:
            organization = {
                "id": str(reuse.organization.id),
                "name": reuse.organization.name,
                "public_service": 1 if reuse.organization.public_service else 0,
                "followers": reuse.organization.metrics.get("followers", 0),
                "badges": [badge.kind for badge in reuse.organization.badges],
            }

        extras = {}
        for key, value in reuse.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value

        return {
            "id": str(reuse.id),
            "title": reuse.title,
            "description": reuse.description,
            "url": reuse.url,
            "created_at": to_iso_datetime(reuse.created_at),
            "last_modified": to_iso_datetime(reuse.last_modified),
            "archived": to_iso_datetime(reuse.archived) if reuse.archived else None,
            "views": reuse.metrics.get("views", 0),
            "followers": reuse.metrics.get("followers", 0),
            "datasets": reuse.metrics.get("datasets", 0),
            "featured": 1 if reuse.featured else 0,
            "organization": organization,
            "owner": str(reuse.owner.id) if reuse.owner else None,
            "type": reuse.type,
            "topic": reuse.topic,  # Metadata topic (health, transport, etc.)
            "topic_object": [
                str(tid) for tid in topic_object_ids
            ],  # Topic objects linked via TopicElement
            "tags": reuse.tags,
            "badges": [badge.kind for badge in reuse.badges],
            "extras": extras,
            "producer_type": get_producer_type(reuse),
        }
