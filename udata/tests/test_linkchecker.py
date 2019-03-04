# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock
import pytest
from datetime import datetime, timedelta

from udata.auth import login_user
from udata.tests import TestCase
from udata.core.activity import init_app as init_activity
from udata.core.activity.models import Activity
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.user.factories import UserFactory
from udata.linkchecker.checker import check_resource
from udata.settings import Testing


class LinkcheckerTestSettings(Testing):
    LINKCHECKING_ENABLED = True
    LINKCHECKING_IGNORE_DOMAINS = ['example-ignore.com']
    LINKCHECKING_MIN_CACHE_DURATION = 0.5
    LINKCHECKING_UNAVAILABLE_THRESHOLD = 100
    LINKCHECKING_MAX_CACHE_DURATION = 100


@pytest.fixture
def activity_app(app):
    init_activity(app)
    yield app


def test_check_resource_creates_no_activity(activity_app, mocker):
    resource = ResourceFactory()
    dataset = DatasetFactory(resources=[resource])
    user = UserFactory()
    login_user(user)
    check_res = {'check:status': 200, 'check:available': True,
                 'check:date': datetime.now()}

    class DummyLinkchecker:
        def check(self, _):
            return check_res
    mocker.patch('udata.linkchecker.checker.get_linkchecker',
                 return_value=DummyLinkchecker)

    check_resource(resource)

    activities = Activity.objects.filter(related_to=dataset)
    assert len(activities) == 0


class LinkcheckerTest(TestCase):
    settings = LinkcheckerTestSettings

    def setUp(self):
        self.resource = ResourceFactory()
        self.dataset = DatasetFactory(resources=[self.resource])

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_no_linkchecker(self, mock_fn):
        mock_fn.return_value = None
        res = check_resource(self.resource)
        self.assertEqual(res, ({'error': 'No linkchecker configured.'}, 503))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_ok(self, mock_fn):
        check_res = {'check:status': 200, 'check:available': True,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        self.assertEqual(res, check_res)
        check_res.update({'check:count-availability': 1})
        self.assertEqual(self.resource.extras, check_res)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_filter_result(self, mock_fn):
        check_res = {'check:status': 200, 'dummy': 'dummy'}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        res = check_resource(self.resource)
        self.assertEqual(res, check_res)
        self.assertNotIn('dummy', self.resource.extras)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_no_status(self, mock_fn):
        class DummyLinkchecker:
            def check(self, _):
                return {'check:available': True}
        mock_fn.return_value = DummyLinkchecker
        res = check_resource(self.resource)
        self.assertEqual(res,
                          ({'error': 'No status in response from linkchecker'},
                           503))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_check_error(self, mock_fn):
        class DummyLinkchecker:
            def check(self, _):
                return {'check:error': 'ERROR'}
        mock_fn.return_value = DummyLinkchecker
        res = check_resource(self.resource)
        self.assertEqual(res, ({'error': 'ERROR'}, 500))

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_check_resource_linkchecker_in_resource(self, mock_fn):
        self.resource.extras['check:checker'] = 'another_linkchecker'
        self.resource.save()
        check_resource(self.resource)
        args, kwargs = mock_fn.call_args
        self.assertEqual(args, ('another_linkchecker', ))

    def test_check_resource_linkchecker_no_check(self):
        self.resource.extras['check:checker'] = 'no_check'
        self.resource.save()
        res = check_resource(self.resource)
        self.assertEqual(res.get('check:status'), 204)
        self.assertEqual(res.get('check:available'), True)

    def test_check_resource_ignored_domain(self):
        self.resource.extras = {}
        self.resource.url = 'http://example-ignore.com/url'
        self.resource.save()
        res = check_resource(self.resource)
        self.assertEqual(res.get('check:status'), 204)
        self.assertEqual(res.get('check:available'), True)

    def test_is_need_check(self):
        self.resource.extras = {'check:available': True,
                                'check:date': datetime.now(),
                                'check:status': 42}
        self.assertFalse(self.resource.need_check())

    def test_is_need_check_unknown_status(self):
        self.resource.extras = {}
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_cache_expired(self):
        self.resource.extras = {
            'check:available': True,
            'check:date': datetime.now() - timedelta(seconds=3600),
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_date_string(self):
        check_date = (datetime.now() - timedelta(seconds=3600)).isoformat()
        self.resource.extras = {
            'check:available': True,
            'check:date': check_date,
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_wrong_check_date(self):
        check_date = '123azerty'
        self.resource.extras = {
            'check:available': True,
            'check:date': check_date,
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_wrong_check_date_int(self):
        check_date = 42
        self.resource.extras = {
            'check:available': True,
            'check:date': check_date,
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_count_availability(self):
        self.resource.extras = {
            # should need a new check after 100 * 30s = 3000s < 3600s
            'check:count-availability': 100,
            'check:available': True,
            'check:date': datetime.now() - timedelta(seconds=3600),
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    def test_is_need_check_count_availability_expired(self):
        self.resource.extras = {
            # should need a new check after 150 * 30s = 4500s > 3600s
            'check:count-availability': 150,
            'check:available': True,
            'check:date': datetime.now() - timedelta(seconds=3600),
            'check:status': 42
        }
        self.assertFalse(self.resource.need_check())

    def test_is_need_check_count_availability_unavailable(self):
        self.resource.extras = {
            # should need a new check after 30s < 3600S
            # count-availability is below threshold
            'check:count-availability': 95,
            'check:available': False,
            'check:date': datetime.now() - timedelta(seconds=3600),
            'check:status': 42
        }
        self.assertTrue(self.resource.need_check())

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_count_availability_increment(self, mock_fn):
        check_res = {'check:status': 200, 'check:available': True,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        check_resource(self.resource)
        self.assertEqual(self.resource.extras['check:count-availability'], 1)

        check_resource(self.resource)
        self.assertEqual(self.resource.extras['check:count-availability'], 2)

    @mock.patch('udata.linkchecker.checker.get_linkchecker')
    def test_count_availability_reset(self, mock_fn):
        self.resource.extras = {'check:status': 200, 'check:available': True,
                                'check:date': datetime.now(),
                                'check:count-availability': 2}
        check_res = {'check:status': 200, 'check:available': False,
                     'check:date': datetime.now()}

        class DummyLinkchecker:
            def check(self, _):
                return check_res
        mock_fn.return_value = DummyLinkchecker

        check_resource(self.resource)
        self.assertEqual(self.resource.extras['check:count-availability'], 1)

    def test_count_availability_threshold(self):
        self.resource.extras = {
            'check:status': 404,
            'check:available': False,
            # if it weren't above threshold, should need check (>30s)
            # and we're still below max_cache 101 * 0.5 < 100
            'check:date': datetime.now() - timedelta(seconds=60),
            'check:count-availability': 101
        }
        self.assertFalse(self.resource.need_check())

    def test_count_availability_max_cache_duration(self):
        self.resource.extras = {
            'check:status': 200,
            'check:available': True,
            # next check should be at 300 * 0.5 = 150min
            # but we are above max cache duration 150min > 100min
            # and 120m > 100 min so we should need a new check
            'check:date': datetime.now() - timedelta(minutes=120),
            'check:count-availability': 300
        }
        self.assertTrue(self.resource.need_check())
