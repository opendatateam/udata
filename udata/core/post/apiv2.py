from flask import abort

from udata import search
from udata.api import API, apiv2, fields

from .models import Post
from .search import PostSearch

ns = apiv2.namespace("posts", "Post related operations")

search_parser = PostSearch.as_request_parser(store_missing=False)

post_page_fields = apiv2.model("PostPage", fields.pager(Post.__read_fields__))


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
