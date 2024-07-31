import datetime

from udata.core.reuse.api import DEFAULT_SORTING, ReuseApiParser
from udata.models import Organization, Reuse, User
from udata.search import (
    BoolFilter,
    Filter,
    ModelSearchAdapter,
    ModelTermsFilter,
    register,
)
from udata.utils import to_iso_datetime

__all__ = ("ReuseSearch",)


@register
class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    search_url = "reuses/"

    sorts = {
        "created": "created_at",
        "datasets": "metrics.datasets",
        "followers": "metrics.followers",
        "views": "metrics.views",
    }

    filters = {
        "tag": Filter(),
        "organization": ModelTermsFilter(model=Organization),
        "owner": ModelTermsFilter(model=User),
        "type": Filter(),
        "badge": Filter(),
        "featured": BoolFilter(),
        "topic": Filter(),
        "archived": BoolFilter(),
    }

    @classmethod
    def is_indexable(cls, reuse: Reuse) -> bool:
        return reuse.deleted is None and len(reuse.datasets) > 0 and not reuse.private

    @classmethod
    def mongo_search(cls, args):
        reuses = Reuse.objects(deleted=None, private__ne=True)
        reuses = ReuseApiParser.parse_filters(reuses, args)

        sort = (
            cls.parse_sort(args["sort"])
            or ("$text_score" if args["q"] else None)
            or DEFAULT_SORTING
        )
        offset = (args["page"] - 1) * args["page_size"]
        return reuses.order_by(sort).skip(offset).limit(args["page_size"]), reuses.count()

    @classmethod
    def serialize(cls, reuse: Reuse) -> dict:
        organization = None
        owner = None
        if reuse.organization:
            org = Organization.objects(id=reuse.organization.id).first()
            organization = {
                "id": str(org.id),
                "name": org.name,
                "public_service": 1 if org.public_service else 0,
                "followers": org.metrics.get("followers", 0),
            }
        elif reuse.owner:
            owner = User.objects(id=reuse.owner.id).first()

        extras = {}
        for key, value in reuse.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value

        return {
            "id": str(reuse.id),
            "title": reuse.title,
            "description": reuse.description,
            "url": reuse.url,
            "created_at": to_iso_datetime(reuse.created_at),
            "archived": to_iso_datetime(reuse.archived) if reuse.archived else None,
            "views": reuse.metrics.get("views", 0),
            "followers": reuse.metrics.get("followers", 0),
            "datasets": reuse.metrics.get("datasets", 0),
            "featured": 1 if reuse.featured else 0,
            "organization": organization,
            "owner": str(owner.id) if owner else None,
            "type": reuse.type,
            "topic": reuse.topic,
            "tags": reuse.tags,
            "badges": [badge.kind for badge in reuse.badges],
            "extras": extras,
        }
