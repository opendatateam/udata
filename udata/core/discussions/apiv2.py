from flask import abort

from udata import search
from udata.api import API, apiv2, fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.user.api_fields import user_ref_fields

from .api import (
    discussion_fields,
    discussion_permissions_fields,
    message_fields,
    message_permissions_fields,
)
from .search import DiscussionSearch

ns = apiv2.namespace("discussions", "Discussion related operations")

search_parser = DiscussionSearch.as_request_parser(store_missing=False)

# Register nested models in apiv2
apiv2.inherit("UserReference", user_ref_fields)
apiv2.inherit("OrganizationReference", org_ref_fields)
apiv2.inherit("DiscussionMessagePermissions", message_permissions_fields)
apiv2.inherit("DiscussionMessage", message_fields)
apiv2.inherit("DiscussionPermissions", discussion_permissions_fields)
apiv2.inherit("Discussion", discussion_fields)
discussion_page_fields = apiv2.model("DiscussionPage", fields.search_pager(discussion_fields))


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
