import itertools
import logging

from elasticsearch_dsl import DocType, Integer, Float, Object
from elasticsearch_dsl.document import DocTypeMeta
from flask_restplus.reqparse import RequestParser
from flask import current_app

from udata.search import es, i18n_analyzer
from udata.search.query import SearchQuery

log = logging.getLogger(__name__)


def config_getter(domain):
    prefix = '_'.join(('SEARCH', domain.upper()))

    def get_config(key, default=None):
        key = '_'.join((prefix, key.upper()))
        return current_app.config.get(key, default)
    return get_config


def lazy_config(domain):
    getter = config_getter(domain)

    def lazy_get_config(key, default=None):
        def lazy():
            return getter(key, default)
        return lazy
    return lazy_get_config


class AdapterMetaclass(DocTypeMeta):
    def __new__(cls, name, bases, attrs):
        new = super(AdapterMetaclass, cls).__new__(cls, name, bases, attrs)
        if new.model:
            getter = config_getter(new.model.__name__.upper())

            @classmethod
            def from_config(cls, key, value=None):
                return getter(key, value)
            new.from_config = from_config
        return new


class ModelSearchAdapter(DocType, metaclass=AdapterMetaclass):
    """This class allow to describe and customize the search behavior."""
    analyzer = i18n_analyzer
    boosters = None
    facets = None
    fuzzy = False
    match_type = 'cross_fields'
    model = None
    exclude_fields = None  # Exclude fields from being fetched on indexation
    sorts = None

    @classmethod
    def doc_type(cls):
        return cls._doc_type.name

    @classmethod
    def is_indexable(cls, document):
        return True

    @classmethod
    def from_model(cls, document):
        """By default use the ``to_dict`` method

        and exclude ``_id``, ``_cls`` and ``owner`` fields
        """
        return cls(meta={'id': document.id}, **cls.serialize(document))

    @classmethod
    def serialize(cls, document):
        """By default use the ``to_dict`` method

        and exclude ``_id``, ``_cls`` and ``owner`` fields
        """
        return document.to_dict(exclude=('_id', '_cls', 'owner'))

    @classmethod
    def completer_tokenize(cls, value, min_length=3):
        '''Quick and dirty tokenizer for completion suggester'''
        tokens = list(itertools.chain(*[
            [m for m in n.split("'") if len(m) >= min_length]
            for n in value.split(' ')
        ]))
        return list(set([value] + tokens + [' '.join(tokens)]))

    @classmethod
    def facet_search(cls, *facets):
        '''
        Build a FacetSearch for a given list of facets

        Elasticsearch DSL doesn't allow to list facets
        once and for all and then later select them.
        They are always all requested

        As we don't use them every time and facet computation
        can take some time, we build the FacetedSearch
        dynamically with only those requested.
        '''
        f = dict((k, v) for k, v in cls.facets.items() if k in facets)

        class TempSearch(SearchQuery):
            adapter = cls
            analyzer = cls.analyzer
            boosters = cls.boosters
            doc_types = cls
            facets = f
            fields = cls.from_config('FIELDS')
            fuzzy = cls.fuzzy
            match_type = cls.match_type
            model = cls.model

        return TempSearch

    @classmethod
    def safe_get(cls, id, **kwargs):
        if 'using' not in kwargs:
            kwargs['using'] = es.client
        return cls.get(id, ignore=404, **kwargs)

    @classmethod
    def exists(cls, id, **kwargs):
        return bool(cls.safe_get(id, **kwargs))

    @classmethod
    def as_request_parser(cls, paginate=True):
        parser = RequestParser()
        # q parameter
        parser.add_argument('q', type=str, location='args',
                            help='The search query')
        # Expected facets
        # (ie. I want all facets or I want both tags and licenses facets)
        facets = list(cls.facets)
        if facets:
            parser.add_argument('facets', type=str, location='args',
                                choices=['all'] + facets,
                                action='append',
                                help='Selected facets to fetch')
        # Add facets filters arguments
        # (apply a value to a facet ie. tag=value)
        for name, facet in cls.facets.items():
            kwargs = facet.as_request_parser_kwargs()
            parser.add_argument(name, location='args', **kwargs)
        # Sort arguments
        keys = list(cls.sorts)
        choices = keys + ['-' + k for k in keys]
        help_msg = 'The field (and direction) on which sorting apply'
        parser.add_argument('sort', type=str, location='args', choices=choices,
                            help=help_msg)
        if paginate:
            parser.add_argument('page', type=int, location='args',
                                default=0, help='The page to display')
            parser.add_argument('page_size', type=int, location='args',
                                default=20, help='The page size')
        return parser
