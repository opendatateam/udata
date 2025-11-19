from udata.tests import PytestOnlyTestCase


class CliBaseTest(PytestOnlyTestCase):
    def test_cli_help(self):
        """Should display help without errors"""
        self.cli()
        self.cli("-?")
        self.cli("-h")
        self.cli("--help")

    def test_cli_log_and_printing(self):
        """Should properly log and print"""
        self.cli("test log")

    def test_cli_version(self):
        """Should display version without errors"""
        self.cli("--version")
