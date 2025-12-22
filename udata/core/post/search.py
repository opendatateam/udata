from udata.core.post.models import Post
from udata.search import Filter, ListFilter, ModelSearchAdapter, register


@register
class PostSearch(ModelSearchAdapter):
    model = Post
    search_url = "posts/"

    sorts = {
        "created": "created_at",
        "last_modified": "last_modified",
        "published": "published",
    }

    filters = {
        "tag": ListFilter(),
        "last_modified_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
    }

    @classmethod
    def is_indexable(cls, post):
        return True

    @classmethod
    def mongo_search(cls, args):
        """Fallback search implementation when search service is not available"""
        posts = Post.objects()
        posts = posts.order_by("-created_at")
        return posts

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

