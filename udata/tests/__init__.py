# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import mock

from contextlib import contextmanager
from urlparse import urljoin

from flask import request, url_for
from flask.ext.testing import TestCase as BaseTestCase

from nose.plugins import Plugin

from udata.app import create_app
from udata.models import db
from udata.search import es

from werkzeug.urls import url_encode

from .factories import UserFactory

# Suppress debug data for third party libraries
for logger in ('factory', 'elasticsearch', 'urllib3'):
    logging.getLogger(logger).setLevel(logging.WARNING)


class UDataNosePlugin(Plugin):
    name = 'udata'
    enabled = True

    def configure(self, options, conf):
        pass  # always on

    # def begin(self):
    #     # Ensure GEvent monkey patching is OK
    #     import sys
    #     if 'threading' in sys.modules:
    #         del sys.modules['threading']
    #     if 'subprocess' in sys.modules:
    #         del sys.modules['subprocess']
    #     from gevent import monkey
    #     monkey.patch_all()


class TestCase(BaseTestCase):
    settings = 'udata.settings.Testing'

    def create_app(self):
        app = create_app(self.settings)
        # Override some local config
        app.config['DEBUG_TOOLBAR'] = False
        app.config['ASSETS_DEBUG'] = True
        app.config['ASSETS_AUTO_BUILD'] = False
        app.config['ASSETS_VERSIONS'] = False
        app.config['ASSETS_URL_EXPIRE'] = False
        app.config['SERVER_NAME'] = 'localhost'
        if not app.config.get('TEST_WITH_PLUGINS', False):
            app.config['PLUGINS'] = []
        if not app.config.get('TEST_WITH_THEME', False):
            app.config['THEME'] = 'default'
        return app

    def login(self, user=None, client=None):
        self.user = user or UserFactory()
        with (client or self.client).session_transaction() as session:
            session['user_id'] = str(self.user.id)
            session['_fresh'] = True
        return self.user


class WebTestMixin(object):
    user = None

    def _build_url(self, url, kwargs):
        if not 'qs' in kwargs:
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
            self.assertNotIn('_flashes', session,
                'There is {0} unexpected flashed message(s): {1}'.format(
                    len(flashes),
                    ', '.join('"{0} ({1})"'.format(msg, cat) for cat, msg in flashes)
                ))


class DBTestMixin(object):
    def tearDown(self):
        '''Clear the database'''
        super(DBTestMixin, self).tearDown()
        db_name = self.app.config['MONGODB_SETTINGS']['DB']
        db.connection.drop_database(db_name)


class SearchTestMixin(DBTestMixin):
    '''A mixin allowing to optionnaly enable indexation and cleanup after'''
    _used_search = False

    def init_search(self):
        self._used_search = True
        self.app.config['AUTO_INDEX'] = True
        es.initialize()

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


def mock_task(name, **kwargs):
    def wrapper(func):
        return mock.patch(name, **kwargs)(func)
    return wrapper
