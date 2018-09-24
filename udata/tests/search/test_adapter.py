# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from flask_restplus import inputs
from flask_restplus.reqparse import RequestParser

from udata import search
from udata.core.metrics import Metric
from udata.i18n import gettext as _
from udata.tests.helpers import assert_json_equal
from udata.utils import clean_string

from . import Fake, FakeSearch, FakeFactory

#############################################################################
#                  Custom search adapters and metrics                       #
#############################################################################

RANGE_LABELS = {
    'none': _('Never reused'),
    'little': _('Little reused'),
    'quite': _('Quite reused'),
    'heavy': _('Heavily reused'),
}


class FakeSearchWithRange(FakeSearch):
    facets = {
        'range': search.RangeFacet(
            field='a_range_field',
            ranges=[
                ('none', (None, 1)),
                ('little', (1, 5)),
                ('quite', (5, 10)),
                ('heavy', (10, None))
            ],
            labels=RANGE_LABELS
        )
    }


class FakeSearchWithBool(FakeSearch):
    facets = {
        'boolean': search.BoolFacet(field='a_bool_field')
    }


class FakeSearchWithCoverage(FakeSearch):
    facets = {
        'coverage': search.TemporalCoverageFacet(field='a_coverage_field')
    }


# Register some metrics for testing

class FakeMetricInt(Metric):
    model = Fake
    name = 'fake-metric-int'


class FakeMetricFloat(Metric):
    model = Fake
    name = 'fake-metric-float'
    value_type = float


#############################################################################
#                                 Helpers                                   #
#############################################################################

def assert_tokens(input, output):
    __tracebackhide__ = True
    assert set(
        search.ModelSearchAdapter.completer_tokenize(input)
    ) == set(output)


def assertHasArgument(parser, name, _type, choices=None):
    __tracebackhide__ = True
    candidates = [
        arg for arg in parser.args if arg.name == name
    ]
    assert len(candidates) == 1, 'Should have strictly one argument'
    arg = candidates[0]
    assert arg.type == _type
    assert not arg.required
    if choices:
        assert set(arg.choices) == set(choices)


#############################################################################
#                                  Tests                                    #
#############################################################################

class SearchAdaptorTest:
    def test_completer_tokenizer(self):
        assert_tokens('test', ['test'])
        assert_tokens('test square', ['test square', 'test', 'square'])
        assert_tokens('test\'s square', ['test\'s square', 'test square', 'test', 'square'])
        assert_tokens('test l\'apostrophe',
                     ['test l\'apostrophe', 'test apostrophe', 'test', 'apostrophe'])

    def test_as_request_parser_terms_facet(self):
        parser = FakeSearch.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + facets selector + tag and other facets + sorts + pagination
        assert len(parser.args) == 7
        assertHasArgument(parser, 'q', unicode)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'tag', clean_string)
        assertHasArgument(parser, 'other', clean_string)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_bool_facet(self):
        parser = FakeSearchWithBool.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + facets selector + boolean facet + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', unicode)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'boolean', inputs.boolean)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_range_facet(self):
        parser = FakeSearchWithRange.as_request_parser()
        facet = FakeSearchWithRange.facets['range']
        assert isinstance(parser, RequestParser)

        # query + facets selector + range facet + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', unicode)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'range', facet.validate_parameter,
                          choices=RANGE_LABELS.keys())
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_temporal_coverage_facet(self):
        parser = FakeSearchWithCoverage.as_request_parser()
        facet = FakeSearchWithCoverage.facets['coverage']
        assert isinstance(parser, RequestParser)

        # query + facets selector + range facet + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', unicode)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'coverage', facet.validate_parameter)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)


@pytest.mark.usefixtures('autoindex')
class IndexingLifecycleTest:
    def test_dont_index_on_creation_if_not_indexable(self):
        '''Should not index an object if it is not indexable'''
        fake = FakeFactory(indexable=False)
        assert not FakeSearch.exists(fake.id)

    def test_index_object_on_creation_if_indexable(self):
        '''Should index an object if it is indexable'''
        fake = FakeFactory(indexable=True)
        assert FakeSearch.exists(fake.id)

    def test_index_object_on_update_if_indexable(self):
        '''Should index an object if it has become indexable'''
        fake = FakeFactory(indexable=False)
        assert not FakeSearch.exists(fake.id)
        fake.indexable = False
        fake.save()
        assert not FakeSearch.exists(fake.id)

    def test_reindex_object_on_update_if_indexable(self):
        '''Should reindex an object if it is still indexable'''
        fake = FakeFactory(indexable=True)
        assert FakeSearch.exists(fake.id)
        fake.title = 'New Title'
        fake.save()
        fake_in_es = FakeSearch.safe_get(fake.id)
        assert fake_in_es is not None
        assert fake_in_es.title == 'New Title'

    def test_unindex_object_if_not_indexable(self):
        '''Should unindex an object if it has become not indexable'''
        fake = FakeFactory(indexable=True)
        assert FakeSearch.exists(fake.id)
        fake.indexable = False
        fake.save()
        assert not FakeSearch.exists(fake.id)

    def test_unindex_object_on_deletion(self):
        '''Should unindex an object on deletion'''
        fake = FakeFactory(indexable=True)
        assert FakeSearch.exists(fake.id)
        fake.delete()
        assert not FakeSearch.exists(fake.id)


@pytest.mark.usefixtures('app')
class MetricsMappingTest:
    def test_map_metrics(self):
        mapping = search.metrics_mapping_for(Fake)
        assert_json_equal(mapping, {
            'type': 'object',
            'properties': {
                'fake-metric-int': {
                    'type': 'integer',
                },
                'fake-metric-float': {
                    'type': 'float',
                },
            }
        })
