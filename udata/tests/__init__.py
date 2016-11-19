# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import logging
import shutil
import tempfile
from datetime import timedelta

import mock

from contextlib import contextmanager
from StringIO import StringIO
from urlparse import urljoin

from flask import request, url_for
from flask_testing import TestCase as BaseTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from udata import settings
from udata.app import create_app
from udata.mail import mail_sent
from udata.models import db
from udata.search import es

from werkzeug.urls import url_encode

from udata.core.user.factories import UserFactory


class TestCase(BaseTestCase):
    settings = settings.Testing

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
        app = create_app(settings.Defaults, override=self.settings)
        return app

    def login(self, user=None, client=None):
        self.user = user or UserFactory()
        with (client or self.client).session_transaction() as session:
            session['user_id'] = str(self.user.id)
            session['_fresh'] = True
        return self.user

    def data(self, filename):
        return os.path.join(os.path.dirname(__file__), 'data', filename)

    def assert201(self, response):
        self.assertStatus(response, 201)

    def assert204(self, response):
        self.assertStatus(response, 204)

    def assert410(self, response):
        self.assertStatus(response, 410)

    def assertEqualDates(self, datetime1, datetime2, limit=1):  # Seconds.
        """Lax date comparison, avoid comparing milliseconds and seconds."""
        delta = (datetime1 - datetime2)
        self.assertTrue(
            timedelta(seconds=-limit) <= delta <= timedelta(seconds=limit))

    def assertStartswith(self, haystack, needle):
        self.assertEqual(
            haystack.startswith(needle), True,
            '{haystack} does not start with {needle}'.format(
                haystack=haystack, needle=needle))

    def assertJsonEqual(self, first, second):
        '''Ensure two dict produce the same JSON'''
        json1 = json.loads(json.dumps(first))
        json2 = json.loads(json.dumps(second))
        self.assertEqual(json1, json2)

    @contextmanager
    def assert_emit(self, *signals):
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
    def capture_mails(self):
        mails = []

        def on_mail_sent(mail):
            mails.append(mail)

        mail_sent.connect(on_mail_sent)

        yield mails

        mail_sent.disconnect(on_mail_sent)


class WebTestMixin(object):
    user = None

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

    def assert_flashes(self, expected_message, expected_category='message'):
        with self.client.session_transaction() as session:
            try:
                category, message = session['_flashes'][0]
            except KeyError:
                raise AssertionError('nothing flashed')
            self.assertIn(expected_message, message)
            self.assertEqual(expected_category, category)

    def assert_not_flash(self):
        with self.client.session_transaction() as session:
            flashes = session.get('_flashes', [])
            self.assertNotIn(
                '_flashes', session,
                'There is {0} unexpected flashed message(s): {1}'.format(
                    len(flashes),
                    ', '.join('"{0} ({1})"'.format(msg, cat)
                              for cat, msg in flashes)
                ))


class DBTestMixin(object):

    def tearDown(self):
        '''Clear the database'''
        super(DBTestMixin, self).tearDown()
        db_name = self.app.config['MONGODB_DB']
        db.connection.client.drop_database(db_name)


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
