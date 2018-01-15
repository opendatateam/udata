# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests import TestCase, CliTestMixin


class CliTest(CliTestMixin, TestCase):
    def test_help(self):
        '''Should display help without errors'''
        self.cli()
        self.cli('-?')
        self.cli('-h')
        self.cli('--help')

    def test_log_and_printing(self):
        '''Should properly log and print'''
        self.cli('test log')

    def test_version(self):
        '''Should display version without errors'''
        self.cli('--version')
