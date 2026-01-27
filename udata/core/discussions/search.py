from udata.core.discussions.models import Discussion
from udata.search import BoolFilter, Filter, ModelSearchAdapter, register


@register
class DiscussionSearch(ModelSearchAdapter):
    model = Discussion
    search_url = "discussions/"

    sorts = {
        "created": "created_at",
        "closed": "closed_at",
    }

    filters = {
        "closed": BoolFilter(),
        "last_update_range": Filter(choices=["last_30_days", "last_12_months", "last_3_years"]),
    }

    @classmethod
    def is_indexable(cls, discussion):
        return True

    @classmethod
    def mongo_search(cls, args):
        """Fallback search implementation when search service is not available"""
        discussions = Discussion.objects()
        discussions = discussions.order_by("-created")
        return discussions

    @classmethod
    def serialize(cls, discussion):
        """Transform a Discussion object into a flat dictionary for indexing."""
        # Concatenate all message contents
        messages_content = []
        for message in discussion.discussion:
            if message.content:
                messages_content.append(message.content)

        subject_class = None
        subject_id = None
        if discussion.subject:
            subject_class = discussion.subject.__class__.__name__
            subject_id = str(discussion.subject.id)

        return {
            "id": str(discussion.id),
            "title": discussion.title,
            "content": " ".join(messages_content),
            "created_at": discussion.created.isoformat() if discussion.created else None,
            "closed_at": discussion.closed.isoformat() if discussion.closed else None,
            "closed": discussion.closed is not None,
            "subject_class": subject_class,
            "subject_id": subject_id,
        }
