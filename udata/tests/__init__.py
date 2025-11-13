import unittest

import pytest
from werkzeug import Response

from udata import settings
from udata.app import UDataApp, create_app
from udata.tests.plugin import TestClient

from . import helpers


class TestCaseMixin:
    app: UDataApp

    def get_settings(self, request):
        """
        This seems really complicated for what it's doing. I think we want to create
        an app with the default setting being `settings.Testing` and some overrides
        from the "options" markers. But to do that `settings.Testing` should inherit from
        `settings.Default`?

        We may also want to prevent loading `udata.cfg` for testing to avoid failing tests
        locally because some config is changed on our computer. Tests should work only with
        default settings (or overrides for a specific test) but not with a local `udata.cfg`.

        Not sure if the plugin situation is still relevant now that plugins are integrated
        into udata.
        """
        return settings.Testing

    @pytest.fixture(autouse=True, name="app")
    def _app(self, request):
        test_settings = self.get_settings(request)
        self.app = create_app(settings.Defaults, override=test_settings)
        self.app.test_client_class = TestClient
        return self.app

    def assertEqualDates(self, datetime1, datetime2, limit=1):  # Seconds.
        """Lax date comparison, avoid comparing milliseconds and seconds."""
        __tracebackhide__ = True
        helpers.assert_equal_dates(datetime1, datetime2, limit=1)

    def assertStreamEqual(self, response1: Response, response2: Response):
        __tracebackhide__ = True
        stream1 = list(response1.iter_encoded())
        stream2 = list(response2.iter_encoded())
        assert stream1 == stream2


class TestCase(TestCaseMixin, unittest.TestCase):
    pass


class PytestOnlyTestCase(TestCaseMixin):
    pass
