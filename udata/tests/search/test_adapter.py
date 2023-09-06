import datetime

from flask import current_app
from flask_restx import inputs
from flask_restx.reqparse import RequestParser
from unittest.mock import patch

from udata import search
from udata.i18n import gettext as _
from udata.utils import clean_string
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


class IndexingLifecycleTest(APITestCase):

    @patch('requests.delete')
    def test_producer_should_send_a_message_without_payload_if_not_indexable(self, mock_req):
        fake_data = DatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))

        search_service_url = current_app.config['SEARCH_SERVICE_API_URL']
        url = f'{search_service_url}{DatasetSearch.search_url}/{str(fake_data.id)}/unindex'
        mock_req.assert_called_with(url)

    @patch('requests.post')
    def test_producer_should_send_a_message_with_payload_if_indexable(self, mock_req):
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        reindex.run(*as_task_param(fake_data))

        expected_value = {
            'document': DatasetSearch.serialize(fake_data)
        }
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}{DatasetSearch.search_url}/index"
        mock_req.assert_called_with(url, json=expected_value)

    @patch('requests.Session.post')
    def test_index_model(self, mock_req):
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        index_model(DatasetSearch, start=None, reindex=False, from_datetime=None)

        expected_value = {
            'document': DatasetSearch.serialize(fake_data),
            'index': 'dataset'
        }
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}/datasets/index"
        mock_req.assert_called_with(url, json=expected_value)

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_reindex_model(self, mock_session, mock_req):
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211')

        index_model(DatasetSearch, start=datetime.datetime(2022, 2, 20, 20, 2), reindex=True)

        # Create index
        expected_value = {
            'index': 'dataset-2022-02-20-20-02'
        }
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}/create-index"
        mock_req.assert_called_with(url, json=expected_value)

        # Index document
        expected_value = {
            'document': DatasetSearch.serialize(fake_data),
            'index': 'dataset-2022-02-20-20-02'
        }
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}/datasets/index"
        mock_session.assert_called_with(url, json=expected_value)

    @patch('requests.Session.post')
    def test_index_model_from_datetime(self, mock_req):
        VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1211',
                              last_modified_internal=datetime.datetime(2020, 1, 1))
        fake_data = VisibleDatasetFactory(id='61fd30cb29ea95c7bc0e1212',
                                          last_modified_internal=datetime.datetime(2022, 1, 1))

        index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2023, 1, 1))
        mock_req.assert_not_called()

        index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2021, 1, 1))

        expected_value = {
            'document': DatasetSearch.serialize(fake_data),
            'index': 'dataset'
        }
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}/datasets/index"
        mock_req.assert_called_with(url, json=expected_value)
