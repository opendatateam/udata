# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock
from datetime import datetime, timedelta

from udata.tests import TestCase
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.linkchecker.checker import check_resource


class LinkcheckerTestSettings():
    LINKCHECKING_ENABLED = True
    LINKCHECKING_IGNORE_DOMAINS = ['example-ignore.com']
    LINKCHECKING_CACHE_DURATION = 30


class LinkcheckerTest(TestCase):
    settings = LinkcheckerTestSettings

    def setUp(self):
        super(LinkcheckerTest, self).setUp()
        self.resource = ResourceFactory()
        self.dataset = DatasetFactory(resources=[self.resource])

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_no_linkchecker(self, mock_fn):
        mock_fn.return_value = None
        res = check_resource(self.resource)
        self.assertEquals(res, ({'error': 'No linkchecker configured.'}, 503))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_ok(self, mock_fn):
        check_res = {'check:status': 200, 'check:available': True,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        self.assertEquals(res, check_res)
        self.assertEquals(self.resource.extras, check_res)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_filter_result(self, mock_fn):
        check_res = {'check:status': 200, 'dummy': 'dummy'}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        self.assertEquals(res, check_res)
        self.assertEquals(self.resource.extras, {'check:status': 200})

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_no_status(self, mock_fn):
        class DummyLinkchecker:
            def check(self, _):
                return {'check:available': True}
        mock_fn.return_value = DummyLinkchecker
        res = check_resource(self.resource)
        self.assertEquals(res,
                          ({'error': 'No status in response from linkchecker'},
                           503))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_check_error(self, mock_fn):
        class DummyLinkchecker:
            def check(self, _):
                return {'check:error': 'ERROR'}
        mock_fn.return_value = DummyLinkchecker
        res = check_resource(self.resource)
        self.assertEquals(res, ({'error': 'ERROR'}, 500))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_in_resource(self, mock_fn):
        self.resource.extras['check:checker'] = 'another_linkchecker'
        self.resource.save()
        check_resource(self.resource)
        args, kwargs = mock_fn.call_args
        self.assertEquals(args, ('another_linkchecker', ))

    def test_check_resource_linkchecker_no_check(self):
        self.resource.extras['check:checker'] = 'no_check'
        self.resource.save()
        res = check_resource(self.resource)
        self.assertEquals(res.get('check:status'), 204)
        self.assertEquals(res.get('check:available'), True)

    def test_check_resource_ignored_domain(self):
        self.resource.extras = {}
        self.resource.url = 'http://example-ignore.com/url'
        self.resource.save()
        res = check_resource(self.resource)
        self.assertEquals(res.get('check:status'), 204)
        self.assertEquals(res.get('check:available'), True)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_valid_cache(self, mock_fn):
        self.resource.extras = {'check:date': datetime.now(),
                                'check:status': 42}

        check_res = {'check:status': 200, 'check:available': True,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        # we get the result from cache and not from DummyLinkchecker
        self.assertEquals(res, self.resource.extras)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_unvalid_cache(self, mock_fn):
        self.resource.extras = {
            'check:date': datetime.now() - timedelta(seconds=3600),
            'check:status': 42
        }

        check_res = {'check:status': 200, 'check:available': True,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        # we get the result from DummyLinkchecker and not from cache
        self.assertEquals(res, check_res)
