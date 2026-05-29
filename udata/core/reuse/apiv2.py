import mongoengine
from flask import url_for
from flask_login import current_user

from udata import search
from udata.api import API, apiv2, fields
from udata.core.reuse.models import Reuse

from .api_fields import reuse_permissions_fields
from .search import ReuseSearch

DEFAULT_PAGE_SIZE = 50

apiv2.inherit("ReusePermissions", reuse_permissions_fields)
apiv2.inherit("Reuse (read)", Reuse.__read_fields__)

#: Lightweight reuse model: the `datasets` reference list is replaced by a link
#: to the datasets listing endpoint filtered on this reuse, so that listing
#: reuses does not dereference every linked dataset.
reuse_fields = apiv2.clone(
    "Reuse",
    Reuse.__read_fields__,
    {
        "datasets": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "apiv2.datasets",
                    reuse=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                # The list endpoint fetches reuses with `no_dereference()`, so
                # `datasets` holds raw references: len() counts them without
                # triggering a query per linked dataset.
                "total": len(o.datasets),
            },
            description="Link to the reuse datasets",
        ),
    },
)

reuse_page_fields = apiv2.model("ReusePage", fields.pager(reuse_fields))
reuse_search_page_fields = apiv2.model("ReuseSearchPage", fields.search_pager(reuse_fields))

ns = apiv2.namespace("reuses", "Reuse related operations")

search_parser = ReuseSearch.as_request_parser(store_missing=False)


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


@ns.route("/", endpoint="reuses")
class ReuseListAPI(API):
    """Reuses collection endpoint"""

    @apiv2.doc("list_reuses")
    @apiv2.expect(Reuse.__index_parser__)
    @apiv2.marshal_with(reuse_page_fields)
    def get(self):
        """List all reuses"""
        # `no_dereference()` keeps `datasets` as raw references so the lightweight
        # `reuse_fields` model can count them without dereferencing each dataset.
        query = Reuse.objects.no_dereference().visible_by_user(
            current_user, mongoengine.Q(private__ne=True, deleted=None)
        )
        return Reuse.apply_pagination(Reuse.apply_sort_filters(query))
