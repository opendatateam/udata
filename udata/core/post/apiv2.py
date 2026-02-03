from flask import abort

from udata import search
from udata.api import API, apiv2, fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.pages.models import Page, page_permissions_fields
from udata.core.reuse.models import Reuse
from udata.core.user.api_fields import user_ref_fields

from .models import Post
from .search import PostSearch

ns = apiv2.namespace("posts", "Post related operations")

search_parser = PostSearch.as_request_parser(store_missing=False)

# Register nested models in apiv2
apiv2.inherit("UserReference", user_ref_fields)
apiv2.inherit("OrganizationReference", org_ref_fields)
apiv2.inherit("DatasetReference", dataset_fields)
apiv2.inherit("ReuseReference", Reuse.__ref_fields__)
# TODO: Page is a transitive dependency of Post (via content_as_page field).
# We should find a better way to automatically register nested models in apiv2.
apiv2.inherit("PagePermissions", page_permissions_fields)
apiv2.inherit("Page (read)", Page.__read_fields__)
apiv2.inherit("Post (read)", Post.__read_fields__)
post_page_fields = apiv2.model("PostPage", fields.search_pager(Post.__read_fields__))


@ns.route("/search/", endpoint="post_search")
class PostSearchAPI(API):
    """Posts collection search endpoint (backed by search-service when enabled)."""

    @apiv2.doc("search_posts")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(post_page_fields)
    def get(self):
        """List or search all posts"""
        args = search_parser.parse_args()
        try:
            return search.query(PostSearch, **args)
        except NotImplementedError:
            abort(501, "Search endpoint not enabled")
        except RuntimeError:
            abort(500, "Internal search service error")
