from udata import search
from udata.api import API, apiv2, fields
from udata.core.reuse.models import Reuse

from .api_fields import reuse_permissions_fields
from .search import ReuseSearch

apiv2.inherit("ReusePermissions", reuse_permissions_fields)
apiv2.inherit("ReusePage", Reuse.__page_fields__)
apiv2.inherit("Reuse (read)", Reuse.__read_fields__)
reuse_search_page_fields = apiv2.model(
    "ReuseSearchPage", fields.search_pager(Reuse.__read_fields__)
)

ns = apiv2.namespace("reuses", "Reuse related operations")

search_parser = ReuseSearch.as_request_parser(store_missing=False)

DEFAULT_SORTING = "-created_at"


@ns.route("/search/", endpoint="reuse_search")
class ReuseSearchAPI(API):
    """Reuses collection search endpoint"""

    @apiv2.doc("search_reuses")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(reuse_search_page_fields)
    def get(self):
        """Search all reuses"""
        args = search_parser.parse_args()
        return search.query(ReuseSearch, **args)
