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
    def is_indexable(cls, post: Post) -> bool:
        # Unpublished posts are drafts: they must never reach the search index,
        # which is public and unauthenticated.
        return post.published is not None

    @classmethod
    def mongo_search(cls, args):
        posts = Post.objects().published()
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            posts = posts.search_text(phrase_query)
        if args.get("tag"):
            posts = posts.filter(tags__all=args["tag"])

        sort = (
            cls.parse_sort(args["sort"]) or ("$text_score" if args["q"] else None) or "-created_at"
        )
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
