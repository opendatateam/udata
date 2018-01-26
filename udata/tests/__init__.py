# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import warnings

import mock
import pytest

from contextlib import contextmanager
from StringIO import StringIO

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from udata import settings
from udata.mail import mail_sent
from udata.search import es

from . import helpers


class TestCase(unittest.TestCase):
    settings = settings.Testing

    def setUp(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).setUp()

    def tearsDown(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).tearsDown()

    @pytest.fixture(autouse=True)
    def inject_app(self, app):
        self.app = app
        return self.create_app()

    def create_app(self):
        '''
        Here for compatibility legacy test classes
        '''
        return self.app

    def assertEqualDates(self, datetime1, datetime2, limit=1):  # Seconds.
        """Lax date comparison, avoid comparing milliseconds and seconds."""
        __tracebackhide__ = True
        helpers.assert_equal_dates(datetime1, datetime2, limit=1)

    def assertStartswith(self, haystack, needle):
        __tracebackhide__ = True
        msg = '{haystack} does not start with {needle}'
        assert haystack.startswith(needle), msg.format(
            haystack=haystack, needle=needle
        )

    def assertJsonEqual(self, first, second):
        '''Ensure two dict produce the same JSON'''
        __tracebackhide__ = True
        helpers.assert_json_equal(first, second)

    @contextmanager
    def assert_emit(self, *signals):
        __tracebackhide__ = True
        specs = []

        def handler(sender, **kwargs):
            pass

        for signal in signals:
            m = mock.Mock(spec=handler)
            signal.connect(m, weak=False)
            specs.append((signal, m))

        yield

        for signal, mock_handler in specs:
            signal.disconnect(mock_handler)
            signal_name = getattr(signal, 'name', str(signal))
            self.assertTrue(
                mock_handler.called,
                'Signal "{0}" should have been emitted'.format(signal_name)
            )

    @contextmanager
    def assert_not_emit(self, *signals):
        __tracebackhide__ = True
        specs = []

        def handler(sender, **kwargs):
            pass

        for signal in signals:
            m = mock.Mock(spec=handler)
            signal.connect(m, weak=False)
            specs.append((signal, m))

        yield

        for signal, mock_handler in specs:
            signal.disconnect(mock_handler)
            signal_name = getattr(signal, 'name', str(signal))
            self.assertFalse(
                mock_handler.called,
                'Signal "{0}" should NOT have been emitted'.format(signal_name)
            )

    @contextmanager
    def capture_mails(self):
        mails = []

        def on_mail_sent(mail):
            mails.append(mail)

        mail_sent.connect(on_mail_sent)

        yield mails

        mail_sent.disconnect(on_mail_sent)

    @contextmanager
    def assert_warn(self, warning_cls):
        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter('always', warning_cls)
            yield
            warnings.simplefilter('default', warning_cls)
            assert len(w), 'No warning has been raised'
            warning = w[-1]
            msg = '{0} raised and is not a sublcass of {1}'.format(
                warning.category.__name__, warning_cls.__name__
            )
            assert issubclass(warning.category, DeprecationWarning), msg


class WebTestMixin(object):
    user = None

    @pytest.fixture(autouse=True)
    def inject_client(self, client):
        '''
        Inject test client for compatibility with Flask-Testing.
        '''
        self.client = client

    def get(self, url, **kwargs):
        return self.client.get(url, **kwargs)

    def post(self, url, data=None, **kwargs):
        return self.client.post(url, data=data, **kwargs)

    def put(self, url, data=None, **kwargs):
        return self.client.put(url, data=data, **kwargs)

    def delete(self, url, data=None, **kwargs):
        return self.client.delete(url, data=data, **kwargs)

    def assertRedirects(self, response, location, message=None):
        """
        Checks if response is an HTTP redirect to the
        given location.
        :param response: Flask response
        :param location: relative URL path to SERVER_NAME or an absolute URL
        """
        __tracebackhide__ = True
        helpers.assert_redirects(response, location, message=message)

    def assertStatus(self, response, status_code, message=None):
        __tracebackhide__ = True
        helpers.assert_status(response, status_code, message=message)

    def full_url(self, *args, **kwargs):
        __tracebackhide__ = True
        return helpers.full_url(*args, **kwargs)

    def login(self, user=None):
        self.user = self.client.login(user)
        return self.user


for code in 200, 201, 204, 400, 401, 403, 404, 410, 500:
    name = 'assert{0}'.format(code)
    helper = getattr(helpers, name)
    setattr(WebTestMixin, name, lambda s, r, h=helper: h(r))


@pytest.mark.usefixtures('clean_db')
class DBTestMixin(object):
    pass


class SearchTestMixin(DBTestMixin):
    '''A mixin allowing to optionnaly enable indexation and cleanup after'''
    _used_search = False

    def init_search(self):
        self._used_search = True
        self.app.config['AUTO_INDEX'] = True
        es.initialize()
        es.cluster.health(wait_for_status='yellow', request_timeout=10)

    @contextmanager
    def autoindex(self):
        self.init_search()
        yield
        es.indices.refresh(index=es.index_name)

    def tearDown(self):
        '''Drop indices if needed'''
        super(SearchTestMixin, self).tearDown()
        if self._used_search and es.indices.exists(index=es.index_name):
            es.indices.delete(index=es.index_name)
