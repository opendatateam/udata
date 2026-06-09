import logging

from bson import DBRef, ObjectId
from mongoengine.signals import post_save

from udata.flask_mongoengine.document import BaseQuerySet
from udata.utils import Paginable

log = logging.getLogger(__name__)


class DBPaginator(Paginable):
    """A simple paginable implementation"""

    def __init__(self, queryset):
        self.queryset = queryset

    def __iter__(self):
        return iter(self.queryset.items)

    def __len__(self):
        return len(self.queryset.items)

    @property
    def page(self):
        return self.queryset.page

    @property
    def page_size(self):
        return self.queryset.per_page

    @property
    def total(self):
        return self.queryset.total

    @property
    def objects(self):
        return self.queryset.items


class UDataQuerySet(BaseQuerySet):
    def paginate(self, page, per_page, **kwargs):
        result = super(UDataQuerySet, self).paginate(page, per_page)
        return DBPaginator(result)

    def bulk_list(self, ids):
        data = self.in_bulk(ids)
        return [data[id] for id in ids]

    def get_or_create(self, **query):
        """
        Atomically retrieve or create a document using findAndModify (modify in MongoEngine).
        We allow to update the model with the `updates`. The raw kwargs are for the filtering and
        the `updates` are only using to set values for the first creation or update the existing one.

        Returns:
            tuple: (document, created)
        """
        updates = query.pop("updates", {})

        # Since `modify` doesn't trigger validation, we need to manually call it here.
        self._document(**query, **updates).validate()

        # If we pass `new=True` we cannot know if the model
        # was recently created or existed before.
        # When passing `new=False` (the default), we get the previous
        # value: `None` if it wasn't existing, the object if it was already
        # existing.
        # This way of doing force us to do a new request to fetch the document
        # after the modify.
        existing_doc_before_upsert = self.filter(
            **query
        ).modify(
            upsert=True,
            **query,  # Require because `updates` can be empty and `modify` crash when no values are provided.
            **updates,
        )

        # We may avoid this query if `existing_doc_before_upsert` is not `None`
        # by updating the local document with the new values (but the database may
        # have updates too? default values?).
        document = self.get(**query)
        created = existing_doc_before_upsert is None
        if created:
            post_save.send(document.__class__, document=document)

        return document, created

    def generic_in(self, **kwargs):
        """Bypass buggy GenericReferenceField querying issue"""
        query = {}
        for key, value in kwargs.items():
            if not value:
                continue
            # Optimize query for when there is only one value
            if isinstance(value, (list, tuple)) and len(value) == 1:
                value = value[0]
            if isinstance(value, (list, tuple)):
                if all(isinstance(v, str) for v in value):
                    ids = [ObjectId(v) for v in value]
                    query["{0}._ref.$id".format(key)] = {"$in": ids}
                elif all(isinstance(v, DBRef) for v in value):
                    query["{0}._ref".format(key)] = {"$in": value}
                elif all(isinstance(v, ObjectId) for v in value):
                    query["{0}._ref.$id".format(key)] = {"$in": value}
            elif isinstance(value, ObjectId):
                query["{0}._ref.$id".format(key)] = value
            elif isinstance(value, str):
                query["{0}._ref.$id".format(key)] = ObjectId(value)
            else:
                self.error("expect a list of string, ObjectId or DBRef")
        return self(__raw__=query)


def paginate_embedded_list(
    document_cls, document_id, field, embedded_cls, *, page, page_size, condition=None
):
    """Filter and slice an embedded-document ``ListField`` server-side via an
    aggregation, so a document with a huge list isn't fully loaded just to serve
    a single page.

    ``condition`` is an optional aggregation boolean expression over the
    ``$$item`` variable (e.g. ``{"$eq": ["$$item.type", "main"]}``). Returns a
    ``(items, total)`` tuple where ``items`` are rebuilt ``embedded_cls``
    instances and ``total`` is the count after filtering.
    """
    source = f"${field}"
    filtered = (
        {"$filter": {"input": source, "as": "item", "cond": condition}} if condition else source
    )
    offset = page_size * (page - 1) if page > 1 else 0
    pipeline = [
        {"$match": {"_id": document_id}},
        {"$project": {"items": filtered}},
        {
            "$project": {
                "total": {"$size": "$items"},
                "data": {"$slice": ["$items", offset, page_size]},
            }
        },
    ]
    result = next(document_cls.objects.aggregate(*pipeline), None)
    if not result:
        return [], 0
    return [embedded_cls._from_son(item) for item in result["data"]], result["total"]
