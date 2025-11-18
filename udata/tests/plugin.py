import shlex
from contextlib import contextmanager

import pytest
from flask import template_rendered, url_for
from lxml import etree

from .helpers import assert200, assert_command_ok


@pytest.fixture(name="cli")
def cli_fixture(app):
    def mock_runner(*args, **kwargs):
        from udata.commands import cli

        if len(args) == 1 and " " in args[0]:
            args = shlex.split(args[0])
        runner = app.test_cli_runner()
        result = runner.invoke(cli, args, catch_exceptions=False)
        if kwargs.get("check", True):
            assert_command_ok(result)
        return result

    return mock_runner


@pytest.fixture
def instance_path(app, tmpdir):
    """Use temporary application instance_path"""
    from udata.core import storages

    app.instance_path = str(tmpdir)
    app.config["FS_ROOT"] = str(tmpdir / "fs")
    # Force local storage:
    for s in "resources", "avatars", "logos", "images", "chunks", "tmp":
        key = "{0}_FS_{{0}}".format(s.upper())
        app.config[key.format("BACKEND")] = "local"
        app.config.pop(key.format("ROOT"), None)

    storages.init_app(app)

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

        msg = "Template %s not used. Templates were used: %s" % (
            name,
            " ".join(repr(used_templates)),
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
        raise ContextVariableDoesNotExist()


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
    """A requests-mock fixture"""
    import requests_mock

    with requests_mock.Mocker() as m:
        m.ANY = requests_mock.ANY
        yield m


class SitemapClient:
    # Needed for lxml XPath not supporting default namespace
    NAMESPACES = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    MISMATCH = 'URL "{0}" {1} mismatch: expected "{2}" found "{3}"'

    def __init__(self, client):
        self.client = client
        self._sitemap = None

    def fetch(self, secure=False):
        base_url = "{0}://local.test".format("https" if secure else "http")
        response = self.client.get("sitemap.xml", base_url=base_url)
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
        """
        Check than a URL is present in the sitemap
        with given `priority` and `changefreq`
        """
        __tracebackhide__ = True
        r = url.xpath("s:priority", namespaces=self.NAMESPACES)
        assert len(r) == 1, 'URL "{0}" should have one priority'.format(url)
        found = r[0].text
        msg = self.MISMATCH.format(url, "priority", priority, found)
        assert found == str(priority), msg

        r = url.xpath("s:changefreq", namespaces=self.NAMESPACES)
        assert len(r) == 1, 'URL "{0}" should have one changefreq'.format(url)
        found = r[0].text
        msg = self.MISMATCH.format(url, "changefreq", changefreq, found)
        assert found == changefreq, msg


@pytest.fixture
def sitemap(client):
    sitemap_client = SitemapClient(client)
    return sitemap_client
