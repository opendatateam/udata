import logging

from flask_restx.reqparse import RequestParser

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
        return document.to_dict(exclude=("_id", "_cls", "owner"))

    @classmethod
    def is_indexable(cls, document):
        return True

    @classmethod
    def as_request_parser(cls, paginate=True, store_missing: bool = True):
        parser = RequestParser()
        # q parameter
        parser.add_argument(
            "q", type=str, location="args", help="The search query", store_missing=store_missing
        )
        # Add filters arguments
        for name, type in cls.filters.items():
            kwargs = type.as_request_parser_kwargs()
            parser.add_argument(name, location="args", store_missing=store_missing, **kwargs)
        # Sort arguments
        keys = list(cls.sorts)
        choices = keys + ["-" + k for k in keys]
        help_msg = "The field (and direction) on which sorting apply"
        parser.add_argument(
            "sort",
            type=str,
            location="args",
            choices=choices,
            help=help_msg,
            store_missing=store_missing,
        )
        if paginate:
            parser.add_argument(
                "page", type=int, location="args", default=1, help="The page to display"
            )
            parser.add_argument(
                "page_size", type=int, location="args", default=20, help="The page size"
            )
        return parser

    @classmethod
    def parse_sort(cls, sort):
        if sort:
            if sort.startswith("-"):
                # Keyerror because of the '-' character in front of the argument.
                # It is removed to find the value in dict and added back.
                arg_sort = sort[1:]
                sort = "-" + cls.sorts[arg_sort]
            else:
                sort = cls.sorts[sort]
        return sort

    @classmethod
    def temp_search(cls):
        class TempSearch(SearchQuery):
            adapter = cls
            model = cls.model

        return TempSearch
