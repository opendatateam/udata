# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import shutil
import tempfile
import unittest
import warnings

import pytest

from datetime import timedelta

import mock

from contextlib import contextmanager
from StringIO import StringIO
from urlparse import urljoin, urlparse

from flask import request, url_for
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from udata import settings
from udata.app import create_app
from udata.mail import mail_sent
from udata.models import db
from udata.search import es

from werkzeug import cached_property
from werkzeug.urls import url_encode

from udata.core.user.factories import UserFactory


class JsonResponseMixin(object):
    """
    Mixin with testing helper methods
    """
    @cached_property
    def json(self):
        return json.loads(self.data)


def _make_test_response(response_class):
    class TestResponse(response_class, JsonResponseMixin):
        pass

    return TestResponse


class TestCase(unittest.TestCase):
    settings = settings.Testing

    def setUp(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).setUp()

    def tearsDown(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).tearsDown()

    @pytest.fixture(name='app', autouse=True)
    def app_fixture(self):
        return self.create_app()

    def create_app(self):
        '''Create an application a test application.

        - load settings in this order: Default > local > Testing
        - create a minimal application
        - plugins and themes are disabled
        - server name is forced to localhost
        - defaut language is set to EN
        - cache is disabled
        - celery is synchronous
        - CSRF is disabled
        - automatic indexing is disabled
        '''
        # Compatibility with legacy flask testing
        app = self.app = create_app(settings.Defaults, override=self.settings)
        return app

    def data(self, filename):
        return os.path.join(os.path.dirname(__file__), 'data', filename)

    def assertEqualDates(self, datetime1, datetime2, limit=1):  # Seconds.
        """Lax date comparison, avoid comparing milliseconds and seconds."""
        __tracebackhide__ = True
        delta = (datetime1 - datetime2)
        self.assertTrue(
            timedelta(seconds=-limit) <= delta <= timedelta(seconds=limit))

    def assertStartswith(self, haystack, needle):
        __tracebackhide__ = True
        self.assertEqual(
            haystack.startswith(needle), True,
            '{haystack} does not start with {needle}'.format(
                haystack=haystack, needle=needle))

    def assertJsonEqual(self, first, second):
        '''Ensure two dict produce the same JSON'''
        __tracebackhide__ = True
        json1 = json.loads(json.dumps(first))
        json2 = json.loads(json.dumps(second))
        self.assertEqual(json1, json2)

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

    def create_app(self):
        '''
        Inject test client for compatibility with Flask-Testing.
        '''
        # Compatibility with legacy flask testing
        app = super(WebTestMixin, self).create_app()
        app.response_class = _make_test_response(app.response_class)
        self.client = app.test_client()
        return app

    def _build_url(self, url, kwargs):
        if 'qs' not in kwargs:
            return url
        qs = kwargs.pop('qs')
        return '?'.join([url, url_encode(qs)])

    def full_url(self, *args, **kwargs):
        with self.app.test_request_context(''):
            return urljoin(request.url_root, url_for(*args, **kwargs))

    def get(self, url, client=None, **kwargs):
        url = self._build_url(url, kwargs)
        return (client or self.client).get(url, **kwargs)

    def post(self, url, data=None, client=None, **kwargs):
        url = self._build_url(url, kwargs)
        return (client or self.client).post(url, data=data, **kwargs)

    def put(self, url, data=None, client=None, **kwargs):
        url = self._build_url(url, kwargs)
        return (client or self.client).put(url, data=data, **kwargs)

    def delete(self, url, data=None, client=None, **kwargs):
        url = self._build_url(url, kwargs)
        return (client or self.client).delete(url, data=data, **kwargs)

    def assertRedirects(self, response, location, message=None):
        """
        Checks if response is an HTTP redirect to the
        given location.
        :param response: Flask response
        :param location: relative URL path to SERVER_NAME or an absolute URL
        """
        __tracebackhide__ = True
        parts = urlparse(location)

        if parts.netloc:
            expected_location = location
        else:
            server_name = self.app.config.get('SERVER_NAME') or 'localhost'
            expected_location = urljoin("http://%s" % server_name, location)

        valid_status_codes = (301, 302, 303, 305, 307)
        valid_status_code_str = ', '.join(str(code) for code in valid_status_codes)
        not_redirect = "HTTP Status %s expected but got %d" % (valid_status_code_str, response.status_code)
        self.assertTrue(response.status_code in valid_status_codes,
                        message or not_redirect)
        self.assertEqual(response.location, expected_location, message)

    def assertStatus(self, response, status_code, message=None):
        """
        Helper method to check matching response status.

        Extracted from parent class to improve output in case of JSON.

        :param response: Flask response
        :param status_code: response status code (e.g. 200)
        :param message: Message to display on test failure
        """
        __tracebackhide__ = True

        message = message or 'HTTP Status %s expected but got %s' \
                             % (status_code, response.status_code)
        if response.mimetype == 'application/json':
            try:
                second_line = 'Response content is {0}'.format(response.json)
                message = '\n'.join((message, second_line))
            except Exception:
                pass
        assert response.status_code == status_code, message

    def assert200(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 200)

    def assert201(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 201)

    def assert204(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 204)

    def assert400(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 400)

    def assert401(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 401)

    def assert403(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 403)

    def assert404(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 404)

    def assert410(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 410)

    def assert500(self, response):
        __tracebackhide__ = True
        self.assertStatus(response, 500)

    def login(self, user=None, client=None):
        self.user = user or UserFactory()
        with (client or self.client).session_transaction() as session:
            session['user_id'] = str(self.user.id)
            session['_fresh'] = True
        return self.user


class DBTestMixin(object):
    def drop_db(self):
        '''Clear the database'''
        parsed_url = urlparse(self.app.config['MONGODB_HOST'])
        # drop the leading /
        db_name = parsed_url.path[1:]
        db.connection.drop_database(db_name)

    def setUp(self):
        '''Ensure always working on a en empty database'''
        super(DBTestMixin, self).setUp()
        self.drop_db()

    def tearDown(self):
        '''Leave the DB clean'''
        super(DBTestMixin, self).tearDown()
        self.drop_db()


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


class FSTestMixin(object):
    def setUp(self):
        '''Use a temporary FS_ROOT'''
        super(FSTestMixin, self).setUp()
        self.fs_root = tempfile.mkdtemp()
        self.app.config['FS_ROOT'] = self.fs_root

    def tearDown(self):
        '''Clear the temporary file system'''
        super(FSTestMixin, self).tearDown()
        shutil.rmtree(self.fs_root)


class CliTestMixin(object):
    def cli(self, *args):
        from click.testing import CliRunner
        from udata.commands import cli

        if len(args) == 1 and ' ' in args[0]:
            args = args[0].split()

        runner = CliRunner()
        with mock.patch.object(cli, 'create_app', return_value=self.app):
            result = runner.invoke(cli, args, catch_exceptions=False)

        self.assertEqual(result.exit_code, 0,
                         'The command failed with exit code {0.exit_code}'
                         ' and the following output:\n{0.output}'
                         .format(result))
        return result


def mock_task(name, **kwargs):
    def wrapper(func):
        return mock.patch(name, **kwargs)(func)
    return wrapper


def filestorage(filename, content):
    data = (StringIO(str(content))
            if isinstance(content, basestring) else content)
    builder = EnvironBuilder(method='POST', data={
        'file': (data, filename)
    })
    env = builder.get_environ()
    req = Request(env)
    return req.files['file']
