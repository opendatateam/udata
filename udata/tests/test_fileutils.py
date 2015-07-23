# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from udata import fileutils


class TestExtension(unittest.TestCase):
    def test_default(self):
        self.assertEqual(fileutils.extension('test.txt'), 'txt')
        self.assertEqual(fileutils.extension('prefix/test.txt'), 'txt')
        self.assertEqual(fileutils.extension('prefix.with.dot/test.txt'),
                         'txt')

    def test_compound(self):
        self.assertEqual(fileutils.extension('test.tar.gz'), 'tar.gz')
        self.assertEqual(fileutils.extension('prefix.with.dot/test.tar.gz'),
                         'tar.gz')

    def test_no_extension(self):
        self.assertEqual(fileutils.extension('test'), None)
        self.assertEqual(fileutils.extension('prefix/test'), None)
