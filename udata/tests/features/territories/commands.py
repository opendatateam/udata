from udata.tests import TestCase


class CommandsTest(TestCase):
    def test_import_commands(self):
        try:
            from udata.features.territories import commands  # noqa
        except ImportError, e:
            self.fail(e)
