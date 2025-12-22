from flask import abort, request

from udata import search
from udata.api import API, apiv2, fields
from udata.utils import multi_to_dict

from .api import post_fields
from .search import PostSearch

ns = apiv2.namespace("posts", "Post related operations")

search_parser = PostSearch.as_request_parser(store_missing=False)

post_fields_v2 = apiv2.inherit("Post", post_fields)
post_page_fields = apiv2.model("PostPage", fields.pager(post_fields_v2))


@ns.route("/search/", endpoint="post_search")
class PostSearchAPI(API):
    """Posts collection search endpoint (backed by search-service when enabled)."""

    @apiv2.doc("search_posts")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(post_page_fields)
    def get(self):
        """List or search all posts"""
        args = multi_to_dict(request.args)
        try:
            return search.query(PostSearch, **args)
        except NotImplementedError:
            abort(501, "Search endpoint not enabled")
        except RuntimeError:
            abort(500, "Internal search service error")

