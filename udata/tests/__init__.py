import unittest

import pytest
from werkzeug import Response

from udata import settings
from udata.app import UDataApp, create_app

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

    def cli(self, *args, **kwargs):
        """
        Execute a CLI command.

        Usage:
            self.cli("command", "arg1", "arg2")
            self.cli("command arg1 arg2")  # Auto-split on spaces

        Args:
            *args: Command and arguments (can be a single string with spaces or multiple args)
            **kwargs: Additional arguments for the CLI runner (e.g., expect_error=True)

        Returns:
            The CLI result object
        """
        import shlex

        from udata.commands import cli as cli_cmd

        if len(args) == 1 and " " in args[0]:
            args = shlex.split(args[0])

        result = self.app.test_cli_runner().invoke(cli_cmd, args, **kwargs)
        if result.exit_code != 0 and kwargs.get("expect_error") is not True:
            helpers.assert_command_ok(result)
        return result


class TestCase(TestCaseMixin, unittest.TestCase):
    pass


class PytestOnlyTestCase(TestCaseMixin):
    pass
