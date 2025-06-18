from flask import request

from udata import search
from udata.api import API, apiv2
from udata.core.reuse.models import Reuse
from udata.utils import multi_to_dict

from .api_fields import reuse_permissions_fields
from .search import ReuseSearch

apiv2.inherit("ReusePermissions", reuse_permissions_fields)
apiv2.inherit("ReusePage", Reuse.__page_fields__)
apiv2.inherit("Reuse (read)", Reuse.__read_fields__)

ns = apiv2.namespace("reuses", "Reuse related operations")

search_parser = ReuseSearch.as_request_parser()

DEFAULT_SORTING = "-created_at"


@ns.route("/search/", endpoint="reuse_search")
class ReuseSearchAPI(API):
    """Reuses collection search endpoint"""

    @apiv2.doc("search_reuses")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(Reuse.__page_fields__)
    def get(self):
        """Search all reuses"""
        search_parser.parse_args()
        return search.query(ReuseSearch, **multi_to_dict(request.args))
