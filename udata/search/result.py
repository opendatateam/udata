import logging

from bson.objectid import ObjectId

from udata.utils import Paginable

log = logging.getLogger(__name__)


class SearchResult(Paginable):
    """An ElasticSearch result wrapper for easy property access"""

    def __init__(self, query, **kwargs):
        self.query = query
        self.result = kwargs.get("result", None)
        self.mongo_objects = kwargs.get("mongo_objects", None)
        self._page = kwargs.pop("page")
        self._page_size = kwargs.pop("page_size")
        self._total = kwargs.pop("total")

    @property
    def query_string(self):
        return self.query._query

    @property
    def total(self):
        try:
            return self._total
        except (KeyError, AttributeError):
            return 0

    @property
    def page(self):
        return (self.query.page or 1) if self.pages else 1

    @property
    def page_size(self):
        return self._page_size

    @property
    def class_name(self):
        return self.query.adapter.model.__name__

    def get_ids(self):
        try:
            return [elem["id"] for elem in self.result]
        except (KeyError, TypeError):
            return []

    def get_objects(self):
        if not self.mongo_objects:
            ids = [ObjectId(id) for id in self.get_ids()]
            objects = self.query.model.objects.in_bulk(ids)
            self.mongo_objects = [objects.get(id) for id in ids]
            # Filter out DBref ie. indexed object not found in DB
            self.mongo_objects = [o for o in self.mongo_objects if isinstance(o, self.query.model)]
        return self.mongo_objects

    @property
    def objects(self):
        return self.get_objects()

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return self._total

    def __getitem__(self, index):
        return self.get_objects()[index]
