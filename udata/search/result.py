import logging

from bson.objectid import ObjectId

from udata.utils import Paginable


log = logging.getLogger(__name__)


class SearchResult(Paginable):
    '''An ElasticSearch result wrapper for easy property access'''
    def __init__(self, query, result, **kwargs):
        self.query = query
        self.result = result
        self._objects = None
        self._page = kwargs.pop('page')
        self._page_size = kwargs.pop('page_size')
        self._total_pages = kwargs.pop('total_pages')
        self._total = kwargs.pop('total')

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
            return [elem['id'] for elem in self.result]
        except KeyError:
            return []

    def get_objects(self):
        if not self._objects:
            ids = [ObjectId(id) for id in self.get_ids()]
            objects = self.query.model.objects.in_bulk(ids)
            self._objects = [objects.get(id) for id in ids]
            # Filter out DBref ie. indexed object not found in DB
            self._objects = [o for o in self._objects
                             if isinstance(o, self.query.model)]
        return self._objects

    @property
    def objects(self):
        return self.get_objects()

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return len(self.result)

    def __getitem__(self, index):
        return self.get_objects()[index]
