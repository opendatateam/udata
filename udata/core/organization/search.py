import datetime

from udata import search
from udata.core.organization.api import DEFAULT_SORTING, OrgApiParser
from udata.core.organization.constants import PRODUCER_BADGE_TYPES
from udata.models import Organization
from udata.search.fields import ModelTermsFilter
from udata.utils import to_iso_datetime
from udata_search_service.consumers import OrganizationConsumer
from udata_search_service.services import OrganizationService

__all__ = ("OrganizationSearch",)


@search.register
class OrganizationSearch(search.ModelSearchAdapter):
    model = Organization
    service_class = OrganizationService
    consumer_class = OrganizationConsumer

    sorts = {
        "reuses": "metrics.reuses",
        "datasets": "metrics.datasets",
        "followers": "metrics.followers",
        "views": "metrics.views",
        "created": "created_at",
    }

    # Uses __badges__ (not available_badges) so that users can still filter
    # by any existing badge, even hidden ones.
    filters = {
        "badge": ModelTermsFilter(
            model=Organization, field_name="badges", choices=list(Organization.__badges__)
        ),
    }

    @classmethod
    def is_indexable(cls, org: Organization):
        return org.deleted is None

    @classmethod
    def mongo_search(cls, args):
        orgs = Organization.objects.visible()
        orgs = OrgApiParser.parse_filters(orgs, args)

        sort = (
            cls.parse_sort(args["sort"])
            or ("$text_score" if args["q"] else None)
            or DEFAULT_SORTING
        )
        return orgs.order_by(sort).paginate(args["page"], args["page_size"])

    @classmethod
    def serialize(cls, organization):
        extras = {}
        for key, value in organization.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value

        producer_types = []
        if hasattr(organization, "badges") and organization.badges:
            producer_types = [
                badge.kind for badge in organization.badges if badge.kind in PRODUCER_BADGE_TYPES
            ]

        return {
            "id": str(organization.id),
            "name": organization.name,
            "acronym": organization.acronym if organization.acronym else None,
            "description": organization.description,
            "url": organization.url,
            "badges": [badge.kind for badge in organization.badges],
            "producer_type": producer_types,
            "created_at": to_iso_datetime(organization.created_at),
            "orga_sp": 1 if organization.public_service else 0,
            "followers": organization.metrics.get("followers", 0),
            "datasets": organization.metrics.get("datasets", 0),
            "reuses": organization.metrics.get("reuses", 0),
            "views": organization.metrics.get("views", 0),
            "extras": extras,
        }
