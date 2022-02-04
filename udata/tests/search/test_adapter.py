import pytest

from flask_restplus import inputs
from flask_restplus.reqparse import RequestParser
from unittest.mock import Mock

from udata import search
from udata.i18n import gettext as _
from udata.utils import clean_string
from udata.search import KafkaProducerSingleton, reindex, as_task_param
from udata.core.dataset.search import DatasetSearch
from udata.core.dataset.factories import DatasetFactory, VisibleDatasetFactory
from udata.tests.api import APITestCase

from . import FakeSearch

#############################################################################
#                  Custom search adapters and metrics                       #
#############################################################################

RANGE_LABELS = {
    'none': _('Never reused'),
    'little': _('Little reused'),
    'quite': _('Quite reused'),
    'heavy': _('Heavily reused'),
}


class FakeSearchWithBool(FakeSearch):
    filters = {
        'boolean': search.BoolFilter()
    }


class FakeSearchWithCoverage(FakeSearch):
    filters = {
        'coverage': search.TemporalCoverageFilter()
    }


#############################################################################
#                                 Helpers                                   #
#############################################################################

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
    def test_as_request_parser_filter(self):
        parser = FakeSearch.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + tag and other filters + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'tag', clean_string)
        assertHasArgument(parser, 'other', clean_string)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_bool_filter(self):
        parser = FakeSearchWithBool.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + boolean filter + sorts + pagination
        assert len(parser.args) == 5
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'boolean', inputs.boolean)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_temporal_coverage_facet(self):
        parser = FakeSearchWithCoverage.as_request_parser()
        filter = FakeSearchWithCoverage.filters['coverage']
        assert isinstance(parser, RequestParser)

        # query + range facet + sorts + pagination
        assert len(parser.args) == 5
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'coverage', filter.validate_parameter)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)


class IndexingLifecycleTest(APITestCase):

    def test_should_not_index_object_on_update_if_not_indexable(self):
        kafka_mock = Mock()
        KafkaProducerSingleton.get_instance = lambda: kafka_mock
        fake_data = DatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))
        producer = KafkaProducerSingleton.get_instance()

        producer.send.assert_called_with('dataset', key=b'61fd30cb29ea95c7bc0e1211')

    def test_should_index_object_on_update_if_indexable(self):
        kafka_mock = Mock()
        KafkaProducerSingleton.get_instance = lambda: kafka_mock
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))
        producer = KafkaProducerSingleton.get_instance()

        producer.send.assert_called_with('dataset', DatasetSearch.serialize(fake_data), key=b'61fd30cb29ea95c7bc0e1211')
