import datetime

import requests
from bson.objectid import ObjectId
from flask import current_app
from flask_restx.inputs import boolean

from udata.api import api
from udata.api.parsers import ModelApiParser
from udata.core.access_type.constants import AccessType
from udata.core.organization.constants import PRODUCER_TYPES, get_producer_type
from udata.core.topic.models import Topic, TopicElement
from udata.models import Dataservice, Organization, User
from udata.search import (
    BoolFilter,
    Filter,
    ListFilter,
    ModelSearchAdapter,
    ModelTermsFilter,
    register,
)
from udata.utils import to_iso_datetime

# Maximum size in bytes for fetched documentation content
MAX_DOCUMENTATION_SIZE = 1000 * 1024  # 1 MB

__all__ = ("DataserviceSearch",)

DEFAULT_SORTING = "-created_at"


class DataserviceApiParser(ModelApiParser):
    sorts = {
        "created": "created_at",
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument("tag", type=str, location="args")
        self.parser.add_argument("organization", type=str, location="args")
        self.parser.add_argument("is_restricted", type=bool, location="args")
        self.parser.add_argument("featured", type=bool, location="args")

    @staticmethod
    def parse_filters(dataservices, args):
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            dataservices = dataservices.search_text(phrase_query)
        if args.get("tag"):
            dataservices = dataservices.filter(tags=args["tag"])
        if args.get("organization"):
            if not ObjectId.is_valid(args["organization"]):
                api.abort(400, "Organization arg must be an identifier")
            dataservices = dataservices.filter(organization=args["organization"])
        if "is_restricted" in args:
            dataservices = dataservices.filter(
                access_type__in=[AccessType.RESTRICTED]
                if boolean(args["is_restricted"])
                else [AccessType.OPEN, AccessType.OPEN_WITH_ACCOUNT]
            )
        if args.get("featured"):
            dataservices = dataservices.filter(featured=args["featured"])
        return dataservices


@register
class DataserviceSearch(ModelSearchAdapter):
    model = Dataservice
    search_url = "dataservices/"

    sorts = {"created": "created_at", "views": "views", "followers": "followers"}

    filters = {
        "tag": ListFilter(),
        "topic": ModelTermsFilter(model=Topic),
        "organization": ModelTermsFilter(model=Organization),
        "archived": BoolFilter(),
        "featured": BoolFilter(),
        "access_type": Filter(),
        "producer_type": Filter(choices=list(PRODUCER_TYPES)),
        "last_update_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
        "is_restricted": BoolFilter(),
    }

    @classmethod
    def is_indexable(cls, dataservice: Dataservice) -> bool:
        return dataservice.is_visible

    @classmethod
    def fetch_documentation_content(cls, url: str) -> str | None:
        """
        Fetch the content of a documentation URL if it's readable text.
        Returns None if the content cannot be fetched or is not text.
        """
        if not url:
            return None

        try:
            timeout = current_app.config.get("SEARCH_SERVICE_REQUEST_TIMEOUT", 10)
            headers = {"User-Agent": "udata-search-service/1.0"}
            response = requests.get(url, timeout=timeout, stream=True, headers=headers)
            response.raise_for_status()

            if response.encoding is None:
                response.encoding = response.apparent_encoding or "utf-8"

            content_parts = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    chunk_size = len(chunk)
                    if total_size + chunk_size > MAX_DOCUMENTATION_SIZE:
                        remaining = MAX_DOCUMENTATION_SIZE - total_size
                        content_parts.append(chunk[:remaining])
                        break
                    content_parts.append(chunk)
                    total_size += chunk_size

            content = "".join(content_parts)
            return content

        except requests.RequestException:
            return None
        except Exception:
            return None

    @classmethod
    def mongo_search(cls, args):
        dataservices = Dataservice.objects.visible()
        dataservices = DataserviceApiParser.parse_filters(dataservices, args)

        sort = (
            cls.parse_sort(args["sort"])
            or ("$text_score" if args["q"] else None)
            or DEFAULT_SORTING
        )
        return dataservices.order_by(sort).paginate(args["page"], args["page_size"])

    @classmethod
    def serialize(cls, dataservice: Dataservice) -> dict:
        organization = None
        owner = None
        org = None

        topic_ids = list(
            set(te.topic.id for te in TopicElement.objects(element=dataservice) if te.topic)
        )

        if dataservice.organization:
            org = Organization.objects(id=dataservice.organization.id).first()
            organization = {
                "id": str(org.id),
                "name": org.name,
                "public_service": 1 if org.public_service else 0,
                "followers": org.metrics.get("followers", 0),
            }
        elif dataservice.owner:
            owner = User.objects(id=dataservice.owner.id).first()
        extras = {}
        for key, value in dataservice.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value

        documentation_content = cls.fetch_documentation_content(
            dataservice.machine_documentation_url
        )

        return {
            "id": str(dataservice.id),
            "title": dataservice.title,
            "description": dataservice.description,
            "base_api_url": dataservice.base_api_url,
            "created_at": to_iso_datetime(dataservice.created_at),
            "archived": to_iso_datetime(dataservice.archived_at)
            if dataservice.archived_at
            else None,
            "featured": 1 if dataservice.featured else 0,
            "organization": organization,
            "owner": str(owner.id) if owner else None,
            "tags": dataservice.tags,
            "topics": [str(tid) for tid in topic_ids],
            "extras": extras,
            "followers": dataservice.metrics.get("followers", 0),
            "is_restricted": dataservice.access_type == AccessType.RESTRICTED,
            "views": dataservice.metrics.get("views", 0),
            "access_type": dataservice.access_type,
            "producer_type": get_producer_type(org, owner),
            "documentation_content": documentation_content,
        }
