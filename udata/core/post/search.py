from udata.core.post.models import Post
from udata.search import Filter, ListFilter, ModelSearchAdapter, register
from udata_search_service.consumers import PostConsumer
from udata_search_service.services import PostService


@register
class PostSearch(ModelSearchAdapter):
    model = Post
    service_class = PostService
    consumer_class = PostConsumer

    sorts = {
        "created": "created_at",
        "last_modified": "last_modified",
        "published": "published",
    }

    filters = {
        "tag": ListFilter(),
        "last_update_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
    }

    @classmethod
    def is_indexable(cls, post):
        return True

    @classmethod
    def mongo_search(cls, args):
        posts = Post.objects()
        sort = cls.parse_sort(args["sort"]) or "-created_at"
        return posts.order_by(sort).paginate(args["page"], args["page_size"])

    @classmethod
    def serialize(cls, post):
        """Transform a Post object into a flat dictionary for indexing."""
        return {
            "id": str(post.id),
            "name": post.name,
            "headline": post.headline or "",
            "content": post.content,
            "tags": post.tags or [],
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "last_modified": post.last_modified.isoformat() if post.last_modified else None,
            "published": post.published.isoformat() if post.published else None,
        }
