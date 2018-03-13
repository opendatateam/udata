# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
import shlex
import sys

from contextlib import contextmanager
from urlparse import urlparse

from flask import json, template_rendered, url_for
from flask.testing import FlaskClient
from lxml import etree
from werkzeug.urls import url_encode

from udata import settings
from udata.app import create_app
from udata.core.user.factories import UserFactory
from udata.models import db
from udata.search import es

from .helpers import assert200, assert_command_ok


class TestClient(FlaskClient):
    def _build_url(self, url, kwargs):
        if 'qs' not in kwargs:
            return url
        qs = kwargs.pop('qs')
        return '?'.join([url, url_encode(qs)])

    def get(self, url, **kwargs):
        url = self._build_url(url, kwargs)
        return super(TestClient, self).get(url, **kwargs)

    def post(self, url, data=None, **kwargs):
        url = self._build_url(url, kwargs)
        return super(TestClient, self).post(url, data=data, **kwargs)

    def put(self, url, data=None, **kwargs):
        url = self._build_url(url, kwargs)
        return super(TestClient, self).put(url, data=data, **kwargs)

    def delete(self, url, data=None, **kwargs):
        url = self._build_url(url, kwargs)
        return super(TestClient, self).delete(url, data=data, **kwargs)

    def login(self, user=None):
        user = user or UserFactory()
        with self.session_transaction() as session:
            session['user_id'] = str(user.id)
            session['_fresh'] = True
        return user

    def logout(self):
        with self.session_transaction() as session:
            del session['user_id']
            del session['_fresh']


@pytest.fixture
def app(request):
    test_settings = get_settings(request)
    app = create_app(settings.Defaults, override=test_settings)
    app.test_client_class = TestClient
    return app


@pytest.fixture(autouse=True)
def _load_frontend(request, _configure_application):
    '''
    Use `pytest.mark.frontend` to specify that frontend/api should be loaded
    Pass an optionnal list of modules as parameter to restrict loaded modules.

    Handle backward compatibility with Class.modules attribute too

    Properly unload themes when enabled.
    '''
    if 'app' not in request.fixturenames:
        return

    app = request.getfixturevalue('app')
    marker = request.node.get_marker('frontend')
    modules = set(marker.args[0] if marker and marker.args else [])

    if getattr(request.cls, 'modules', None):
        modules |= set(request.cls.modules)

    if marker or hasattr(request.cls, 'modules'):
        from udata import frontend, api
        api.init_app(app)
        frontend.init_app(app, modules)

    if app.config['THEME'] != 'default':
        # Unload theme to allow multiple run with initialization
        from udata import theme
        with app.app_context():
            theme_module = theme.current.entrypoint.module_name

        def unload_theme():
            if theme_module in sys.modules:
                del sys.modules[theme_module]
        request.addfinalizer(unload_theme)


@pytest.fixture
def client(app):
    '''
    Fixes https://github.com/pytest-dev/pytest-flask/issues/42
    '''
    return app.test_client()


def get_settings(request):
    '''
    Extract settings from the current test request
    '''
    marker = request.node.get_marker('settings')
    if marker:
        return marker.args[0]
    return getattr(request.cls, 'settings', settings.Testing)


def drop_db(app):
    '''Clear the database'''
    parsed_url = urlparse(app.config['MONGODB_HOST'])

    # drop the leading /
    db_name = parsed_url.path[1:]
    db.connection.drop_database(db_name)


@pytest.fixture
def clean_db(app):
    drop_db(app)
    yield
    drop_db(app)


class ApiClient(object):
    def __init__(self, client):
        self.client = client
        self._user = None

    @contextmanager
    def user(self, user=None):
        self._user = user or UserFactory()
        if not self._user.apikey:
            self._user.generate_api_key()
            self._user.save()
        yield self._user

    def perform(self, verb, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'

        data = kwargs.get('data')
        if data is not None:
            data = json.dumps(data)
            headers['Content-Length'] = len(data)
            kwargs['data'] = data

        if self._user:
            headers['X-API-KEY'] = kwargs.get('X-API-KEY', self._user.apikey)

        kwargs['headers'] = headers
        method = getattr(self.client, verb)
        return method(url, **kwargs)

    def get(self, url, *args, **kwargs):
        return self.perform('get', url, *args, **kwargs)

    def post(self, url, data=None, json=True, *args, **kwargs):
        if not json:
            return self.client.post(url, data or {}, *args, **kwargs)
        return self.perform('post', url, data=data or {}, *args, **kwargs)

    def put(self, url, data=None, json=True, *args, **kwargs):
        if not json:
            return self.client.put(url, data or {}, *args, **kwargs)
        return self.perform('put', url, data=data or {}, *args, **kwargs)

    def delete(self, url, data=None, *args, **kwargs):
        return self.perform('delete', url, data=data or {}, *args, **kwargs)


@pytest.fixture
def api(client):
    api_client = ApiClient(client)
    return api_client


class AutoIndex(object):
    '''
    Allows to write both::
        with autoindex():
            pass
    and::
        with autoindex:
            pass
    '''
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        es.indices.refresh(index=es.index_name)

    def __call__(self):
        return self


@pytest.fixture
def autoindex(app, clean_db):
    app.config['AUTO_INDEX'] = True
    es.initialize()
    es.cluster.health(wait_for_status='yellow', request_timeout=10)

    yield AutoIndex()

    if es.indices.exists(index=es.index_name):
        es.indices.delete(index=es.index_name)


@pytest.fixture(name='cli')
def cli_fixture(mocker, app):

    def mock_runner(*args, **kwargs):
        from click.testing import CliRunner
        from udata.commands import cli

        if len(args) == 1 and ' ' in args[0]:
            args = shlex.split(args[0])
        runner = CliRunner()
        # Avoid instanciating another app and reuse the app fixture
        with mocker.patch.object(cli, 'create_app', return_value=app):
            result = runner.invoke(cli, args, catch_exceptions=False)
        if kwargs.get('check', True):
            assert_command_ok(result)
        return result

    return mock_runner


@pytest.fixture
def instance_path(app, tmpdir):
    '''Use temporary application instance_path'''
    from udata.core import storages
    from udata.core.storages.views import blueprint

    app.instance_path = str(tmpdir)
    app.config['FS_ROOT'] = str(tmpdir / 'fs')
    # Force local storage:
    for s in 'resources', 'avatars', 'logos', 'images', 'chunks', 'tmp':
        key = '{0}_FS_{{0}}'.format(s.upper())
        app.config[key.format('BACKEND')] = 'local'
        app.config.pop(key.format('ROOT'), None)

    storages.init_app(app)
    app.register_blueprint(blueprint)

    return tmpdir


class ContextVariableDoesNotExist(Exception):
    pass


class TemplateRecorder:
    @contextmanager
    def capture(self):
        self.templates = []
        template_rendered.connect(self._add_template)
        yield
        template_rendered.disconnect(self._add_template)

    def _add_template(self, app, template, context):
        self.templates.append((template, context))

    def assert_used(self, name):
        """
        Checks if a given template is used in the request.

        :param name: template name
        """
        __tracebackhide__ = True

        used_templates = []

        for template, context in self.templates:
            if template.name == name:
                return True

            used_templates.append(template)

        msg = 'Template %s not used. Templates were used: %s' % (
            name, ' '.join(repr(used_templates))
        )
        raise AssertionError(msg)

    def get_context_variable(self, name):
        """
        Returns a variable from the context passed to the template.

        :param name: name of variable
        :raises ContextVariableDoesNotExist: if does not exist.
        """
        for template, context in self.templates:
            if name in context:
                return context[name]
        raise ContextVariableDoesNotExist


@pytest.fixture
def templates():
    recorder = TemplateRecorder()
    with recorder.capture():
        yield recorder


@pytest.fixture
def httpretty():
    import httpretty
    httpretty.reset()
    httpretty.enable()
    yield httpretty
    httpretty.disable()


@pytest.fixture
def rmock():
    '''A requests-mock fixture'''
    import requests_mock
    with requests_mock.Mocker() as m:
        m.ANY = requests_mock.ANY
        yield m


class SitemapClient:
    # Needed for lxml XPath not supporting default namespace
    NAMESPACES = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    MISMATCH = 'URL "{0}" {1} mismatch: expected "{2}" found "{3}"'

    def __init__(self, client):
        self.client = client
        self._sitemap = None

    def fetch(self, secure=False):
        base_url = '{0}://localhost'.format('https' if secure else 'http')
        response = self.client.get('sitemap.xml', base_url=base_url)
        assert200(response)
        self._sitemap = etree.fromstring(response.data)
        return self._sitemap

    def xpath(self, query):
        return self._sitemap.xpath(query, namespaces=self.NAMESPACES)

    def get_by_url(self, endpoint, **kwargs):
        url = url_for(endpoint, _external=True, **kwargs)
        query = 's:url[s:loc="{url}"]'.format(url=url)
        result = self.xpath(query)
        return result[0] if result else None

    def assert_url(self, url, priority, changefreq):
        '''
        Check than a URL is present in the sitemap
        with given `priority` and `changefreq`
        '''
        __tracebackhide__ = True
        r = url.xpath('s:priority', namespaces=self.NAMESPACES)
        assert len(r) == 1, 'URL "{0}" should have one priority'.format(url)
        found = r[0].text
        msg = self.MISMATCH.format(url, 'priority', priority, found)
        assert found == str(priority), msg

        r = url.xpath('s:changefreq', namespaces=self.NAMESPACES)
        assert len(r) == 1, 'URL "{0}" should have one changefreq'.format(url)
        found = r[0].text
        msg = self.MISMATCH.format(url, 'changefreq', changefreq, found)
        assert found == changefreq, msg


@pytest.fixture
def sitemap(client):
    sitemap_client = SitemapClient(client)
    return sitemap_client
