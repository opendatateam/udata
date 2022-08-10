import logging
from webargs import fields, validate
from udata.search.query import SearchQuery


log = logging.getLogger(__name__)


class ModelSearchAdapter:
    """This class allow to describe and customize the search behavior."""
    model = None
    sorts = None
    search_url = None
    filters = {}

    @classmethod
    def serialize(cls, document):
        """By default use the ``to_dict`` method
        and exclude ``_id``, ``_cls`` and ``owner`` fields
        """
        return document.to_dict(exclude=('_id', '_cls', 'owner'))

    @classmethod
    def is_indexable(cls, document):
        return True

    @classmethod
    def as_request_parser(cls, paginate=True):
        search_arguments = {
            "q": fields.Str()
        }
        # Add filters arguments
        for name, filter_type in cls.filters.items():
            search_arguments.update({name: filter_type})

        # Sort arguments
        keys = list(cls.sorts)
        choices = keys + ['-' + k for k in keys]
        search_arguments.update({'sort': fields.Str(validate=validate.OneOf(choices))})

        if paginate:
            search_arguments.update({
                'page': fields.Int(load_default=1),
                'page_size': fields.Int(load_default=20)
            })
        return search_arguments

    @classmethod
    def parse_sort(cls, sort):
        if sort:
            if sort.startswith('-'):
                # Keyerror because of the '-' character in front of the argument.
                # It is removed to find the value in dict and added back.
                arg_sort = sort[1:]
                sort = '-' + cls.sorts[arg_sort]
            else:
                sort = cls.sorts[sort]
        return sort

    @classmethod
    def temp_search(cls):

        class TempSearch(SearchQuery):
            adapter = cls
            model = cls.model

        return TempSearch
