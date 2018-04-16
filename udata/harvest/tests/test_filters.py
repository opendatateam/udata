# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from unittest import TestCase

from voluptuous import Invalid

from udata.harvest import filters

log = logging.getLogger(__name__)


class FiltersTest(TestCase):
    def test_boolean(self):
        true_values = ('1', 'on', 't', 'TRUE', 'true', 'y', 'yes', '  1  ',
                       '  tRuE  ', True, 1, 2, -1)
        false_values = ('0', 'f', 'FALSE', 'false', 'n', 'no', 'off', '  0  ',
                        '  f  ', False, 0)
        none_values = ('', '   ', None)

        for value in true_values:
            self.assertTrue(filters.boolean(value))

        for value in false_values:
            self.assertFalse(filters.boolean(value))

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

    def test_hash(self):
        hashes = {
            'md5': 'bd8668597bfba2d1843441d7199bea65',
            'sha1': 'f2f0249827f501286b4713683e526d541d2cc7e2',
            'sha256': ('c4373e1d81eb44882bf9ff539d0e5f'
                       'faf03a114abf9306591117d781966268f9')
        }

        for type, value in hashes.items():
            self.assertEqual(filters.hash(value),
                             {'type': type, 'value': value})

    def test_unknown_hash(self):
        self.assertEqual(filters.hash('xxxx'), None)
        self.assertEqual(filters.hash(None), None)


class IsUrlFilterTest(TestCase):
    def test_valid_url_with_defaults(self):
        f = filters.is_url()
        self.assertEqual(f('https://somewhere.com/path'),
                         'https://somewhere.com/path')

    def test_allowed_scheme_not_allowed(self):
        f = filters.is_url()
        with self.assertRaises(Invalid):
            f('not-allowed://somewhere.com')

    def test_valid_url_with_default_scheme(self):
        f = filters.is_url()
        self.assertEqual(f('somewhere.com/path'),
                         'http://somewhere.com/path')
