import datetime

from bson.objectid import ObjectId
from flask_restx.inputs import boolean

from udata.api import api
from udata.api.parsers import ModelApiParser
from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_TYPE_OPEN,
    DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
    DATASERVICE_ACCESS_TYPE_RESTRICTED,
)
from udata.models import Dataservice, Organization, User
from udata.search import (
    BoolFilter,
    Filter,
    ModelSearchAdapter,
    ModelTermsFilter,
    register,
)
from udata.utils import to_iso_datetime

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
                access_type__in=[DATASERVICE_ACCESS_TYPE_RESTRICTED]
                if boolean(args["is_restricted"])
                else [DATASERVICE_ACCESS_TYPE_OPEN, DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT]
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
        "tag": Filter(),
        "organization": ModelTermsFilter(model=Organization),
        "archived": BoolFilter(),
        "featured": BoolFilter(),
    }

    @classmethod
    def is_indexable(cls, dataservice: Dataservice) -> bool:
        return dataservice.deleted_at is None and not dataservice.private

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
            "extras": extras,
            "followers": dataservice.metrics.get("followers", 0),
            "is_restricted": dataservice.access_type == DATASERVICE_ACCESS_TYPE_RESTRICTED,
            "views": dataservice.metrics.get("views", 0),
        }
