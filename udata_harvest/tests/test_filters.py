# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from unittest import TestCase

from voluptuous import Invalid

from udata.ext.harvest import filters

log = logging.getLogger(__name__)


class FiltersTest(TestCase):
    def test_boolean(self):
        true_values = ('1', 'on', 't', 'TRUE', 'true', 'y', 'yes', '  1  ',
                       '  tRuE  ', True, 1, 2, -1)
        false_values = ('0', 'f', 'FALSE', 'false', 'n', 'no', 'off', '  0  ',
                        '  f  ', False, 0)
        none_values = ('', '   ', None)

        for value in true_values:
            self.assertEqual(filters.boolean(value), True)

        for value in false_values:
            self.assertEqual(filters.boolean(value), False)

        for value in none_values:
            self.assertIsNone(filters.boolean(value))

        with self.assertRaises(Invalid):
            filters.boolean('vrai')

    def test_empty_none(self):
        empty_values = 0, '', [], {}
        non_empty_values = 'hello', '  hello  '

        for value in empty_values:
            self.assertIsNone(filters.empty_none(value))

        for value in non_empty_values:
            self.assertEqual(filters.empty_none(value), value)

    def test_strip(self):
        self.assertEqual(filters.strip('  hello   '), 'hello')
        self.assertIsNone(filters.strip('    '))

    def test_line_endings(self):
        self.assertEqual(filters.line_endings('hello\r\nworld!\r '),
                         'hello\nworld!\n ')
