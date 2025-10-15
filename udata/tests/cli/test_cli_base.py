from udata.tests import PytestOnlyTestCase


class CliBaseTest(PytestOnlyTestCase):
    def test_cli_help(self, cli):
        """Should display help without errors"""
        cli()
        cli("-?")
        cli("-h")
        cli("--help")

    def test_cli_log_and_printing(self, cli):
        """Should properly log and print"""
        cli("test log")

    def test_cli_version(self, cli):
        """Should display version without errors"""
        cli("--version")
