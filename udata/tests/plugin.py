import pytest

from contextlib import contextmanager
from urlparse import urlparse

from flask import json, template_rendered
from flask.testing import FlaskClient
from werkzeug.urls import url_encode

from udata import settings
from udata.app import create_app
from udata.core.user.factories import UserFactory
from udata.models import db
from udata.search import es


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


@pytest.fixture
def app(request):
    test_settings, extra = get_settings(request)
    app = create_app(settings.Defaults, override=test_settings)
    app.test_client_class = TestClient
    for key, value in extra.items():
        app.config[key] = value

    if request.cls and hasattr(request.cls, 'modules'):
        from udata import frontend, api
        api.init_app(app)
        frontend.init_app(app, request.cls.modules)
    return app


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
        cls = marker.args[0] if len(marker.args) else settings.Testing
        return cls, marker.kwargs
    return getattr(request.cls, 'settings', settings.Testing), {}


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


@pytest.fixture
def autoindex(app, clean_db):
    app.config['AUTO_INDEX'] = True
    es.initialize()
    es.cluster.health(wait_for_status='yellow', request_timeout=10)

    @contextmanager
    def cm():
        yield
        es.indices.refresh(index=es.index_name)

    yield cm

    if es.indices.exists(index=es.index_name):
        es.indices.delete(index=es.index_name)


@pytest.fixture(name='cli')
def cli_fixture(mocker, app):

    def mock_runner(*args):
        from click.testing import CliRunner
        from udata.commands import cli

        if len(args) == 1 and ' ' in args[0]:
            args = args[0].split()
        runner = CliRunner()
        # Avoid instanciating another app and reuse the app fixture
        with mocker.patch.object(cli, 'create_app', return_value=app):
            return runner.invoke(cli, args, catch_exceptions=False)

    return mock_runner


@pytest.fixture
def instance_path(app, tmpdir):
    '''Use temporary application instance_path'''
    from udata.core import storages
    from udata.core.storages.views import blueprint

    app.instance_path = str(tmpdir)
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
