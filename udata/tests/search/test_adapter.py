import datetime
import pytest

from flask_restplus import inputs
from flask_restplus.reqparse import RequestParser
from unittest.mock import Mock

from udata import search
from udata.i18n import gettext as _
from udata.utils import clean_string
from udata_event_service.producer import KafkaProducerSingleton
from udata.search import reindex, as_task_param
from udata.search.commands import index_model
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


@pytest.mark.usefixtures('enable_kafka')
class IndexingLifecycleTest(APITestCase):

    def test_producer_should_send_a_message_without_payload_if_not_indexable(self):
        KafkaProducerSingleton.get_instance = Mock()
        fake_data = DatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))
        producer = KafkaProducerSingleton.get_instance(None)

        expected_value = {
            'service': 'udata',
            'value': DatasetSearch.serialize(fake_data),
            'meta': {
                'message_type': 'dataset.unindex',
                'index': 'dataset'
            }
        }
        topic = self.app.config['UDATA_INSTANCE_NAME'] + '.dataset.unindex'
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=b'61fd30cb29ea95c7bc0e1211')

    def test_producer_should_send_a_message_with_payload_if_indexable(self):
        KafkaProducerSingleton.get_instance = Mock()
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))
        producer = KafkaProducerSingleton.get_instance(None)

        expected_value = {
            'service': 'udata',
            'value': DatasetSearch.serialize(fake_data),
            'meta': {
                'message_type': 'dataset.index',
                'index': 'dataset'
            }
        }
        topic = self.app.config['UDATA_INSTANCE_NAME'] + '.dataset.index'
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=b'61fd30cb29ea95c7bc0e1211')

    def test_index_model(self):
        KafkaProducerSingleton.get_instance = Mock()
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        producer = KafkaProducerSingleton.get_instance(None)

        index_model(DatasetSearch, start=None, reindex=False, from_datetime=None)

        expected_value = {
            'service': 'udata',
            'value': DatasetSearch.serialize(fake_data),
            'meta': {
                'message_type': 'dataset.index',
                'index': 'dataset'
            }
        }
        topic = self.app.config['UDATA_INSTANCE_NAME'] + '.dataset.index'
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=b'61fd30cb29ea95c7bc0e1211')

    def test_reindex_model(self):
        KafkaProducerSingleton.get_instance = Mock()
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        producer = KafkaProducerSingleton.get_instance(None)

        index_model(DatasetSearch, start=datetime.datetime(2022, 2, 20, 20, 2), reindex=True)

        expected_value = {
            'service': 'udata',
            'value': DatasetSearch.serialize(fake_data),
            'meta': {
                'message_type': 'dataset.reindex',
                'index': 'dataset-2022-02-20-20-02'
            }
        }
        topic = self.app.config['UDATA_INSTANCE_NAME'] + '.dataset.reindex'
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=b'61fd30cb29ea95c7bc0e1211')

    def test_index_model_from_datetime(self):
        KafkaProducerSingleton.get_instance = Mock()
        VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211', last_modified=datetime.datetime(2020, 1, 1))
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1212', last_modified = datetime.datetime(2022, 1, 1))

        producer = KafkaProducerSingleton.get_instance(None)

        index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2023, 1, 1))
        producer.send.assert_not_called()

        index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2021, 1, 1))

        expected_value = {
            'service': 'udata',
            'value': DatasetSearch.serialize(fake_data),
            'meta': {
                'message_type': 'dataset.index',
                'index': 'dataset'
            }
        }
        topic = self.app.config['UDATA_INSTANCE_NAME'] + '.dataset.index'
        producer.send.assert_called_with(topic=topic, value=expected_value,
                                         key=b'61fd30cb29ea95c7bc0e1212')
