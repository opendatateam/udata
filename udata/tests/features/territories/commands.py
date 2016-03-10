# -*- coding: utf-8 -*-

from udata.tests import TestCase


class CommandsTest(TestCase):
    def test_import_commands(self):
        try:
            from udata.features.territories import commands
        except ImportError, e:
            self.fail(e)
