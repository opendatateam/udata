from flask import abort

from udata import search
from udata.api import API, apiv2, fields

from .api import discussion_fields
from .search import DiscussionSearch

ns = apiv2.namespace("discussions", "Discussion related operations")

search_parser = DiscussionSearch.as_request_parser(store_missing=False)

discussion_fields_v2 = apiv2.inherit("Discussion", discussion_fields)
discussion_page_fields = apiv2.model("DiscussionPage", fields.pager(discussion_fields_v2))


@ns.route("/search/", endpoint="discussion_search")
class DiscussionSearchAPI(API):
    """Discussions collection search endpoint (backed by search-service when enabled)."""

    @apiv2.doc("search_discussions")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(discussion_page_fields)
    def get(self):
        """List or search all discussions"""
        args = search_parser.parse_args()
        try:
            return search.query(DiscussionSearch, **args)
        except NotImplementedError:
            abort(501, "Search endpoint not enabled")
        except RuntimeError:
            abort(500, "Internal search service error")
