import unittest

import pytest
from werkzeug import Response

from udata import settings
from udata.app import UDataApp, create_app
from udata.tests.plugin import TestClient, get_settings

from . import helpers


class TestCaseMixin:
    settings = settings.Testing
    app: UDataApp

    @pytest.fixture(autouse=True, name="app")
    def _app(self, request):
        test_settings = get_settings(request)
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
