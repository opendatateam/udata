import pytest

from flask_restplus import inputs
from flask_restplus.reqparse import RequestParser

from udata import search
from udata.i18n import gettext as _
from udata.utils import clean_string

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
    facets = {
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

        # query + facets selector + tag and other facets + sorts + pagination
        assert len(parser.args) == 7
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'tag', clean_string)
        assertHasArgument(parser, 'other', clean_string)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_bool_filter(self):
        parser = FakeSearchWithBool.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + facets selector + boolean facet + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'boolean', inputs.boolean)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_temporal_coverage_facet(self):
        parser = FakeSearchWithCoverage.as_request_parser()
        filter = FakeSearchWithCoverage.filters['coverage']
        assert isinstance(parser, RequestParser)

        # query + facets selector + range facet + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, 'q', str)
        assertHasArgument(parser, 'sort', str)
        assertHasArgument(parser, 'facets', str)
        assertHasArgument(parser, 'coverage', filter.validate_parameter)
        assertHasArgument(parser, 'page', int)
        assertHasArgument(parser, 'page_size', int)
