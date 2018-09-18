# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools
import logging

from elasticsearch_dsl import DocType, Integer, Float, Object
from flask_restplus.reqparse import RequestParser

from udata.search import es, i18n_analyzer
from udata.search.query import SearchQuery
from udata.core.metrics import Metric

log = logging.getLogger(__name__)


class ModelSearchAdapter(DocType):
    """This class allow to describe and customize the search behavior."""
    analyzer = i18n_analyzer
    boosters = None
    facets = None
    fields = None
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
            [m for m in n.split("'") if len(m) > min_length]
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
            fields = cls.fields
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
        parser.add_argument('q', type=unicode, location='args',
                            help='The search query')
        # Expected facets
        # (ie. I want all facets or I want both tags and licenses facets)
        facets = cls.facets.keys()
        if facets:
            parser.add_argument('facets', type=str, location='args',
                                choices=['all'] + facets, action='append',
                                help='Selected facets to fetch')
        # Add facets filters arguments
        # (apply a value to a facet ie. tag=value)
        for name, facet in cls.facets.items():
            kwargs = facet.as_request_parser_kwargs()
            parser.add_argument(name, location='args', **kwargs)
        # Sort arguments
        keys = cls.sorts.keys()
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


metrics_types = {
    int: Integer,
    float: Float,
}


def metrics_mapping_for(cls):
    props = {}
    for name, metric in Metric.get_for(cls).items():
        props[metric.name] = metrics_types[metric.value_type]()
    return Object(properties=props)
