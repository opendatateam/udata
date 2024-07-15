import logging

from bson import DBRef, ObjectId
from flask_mongoengine import BaseQuerySet

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

    def get_or_create(self, write_concern=None, auto_save=True, *q_objs, **query):
        """Retrieve unique object or create, if it doesn't exist.

        Returns a tuple of ``(object, created)``, where ``object`` is
        the retrieved or created object and ``created`` is a boolean
        specifying whether a new object was created.

        Taken back from:

        https://github.com/MongoEngine/mongoengine/
        pull/1029/files#diff-05c70acbd0634d6d05e4a6e3a9b7d66b
        """
        defaults = query.pop("defaults", {})
        try:
            doc = self.get(*q_objs, **query)
            return doc, False
        except self._document.DoesNotExist:
            query.update(defaults)
            doc = self._document(**query)

            if auto_save:
                doc.save(write_concern=write_concern)
            return doc, True

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
