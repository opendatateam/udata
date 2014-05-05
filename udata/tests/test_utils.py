# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from datetime import date

from udata.utils import get_by, daterange_start, daterange_end

TEST_LIST = [
    {'name': 'aaa', 'other': 'bbb'},
    {'name': 'bbb', 'another': 'ddd'},
    {'name': 'ccc', 'other': 'bbb'},
]


class ObjDict(object):
    def __init__(self, d):
        self.__dict__.update(d)


class GetByFieldTest(unittest.TestCase):
    def test_find_dict(self):
        '''get_by() should find a dictionnary in list'''
        result = get_by(TEST_LIST, 'name', 'bbb')
        self.assertEqual(result, {'name': 'bbb', 'another': 'ddd'})

    def test_find_object(self):
        '''get_by() should find an object in list'''
        obj_lst = [ObjDict(d) for d in TEST_LIST]
        result = get_by(obj_lst, 'name', 'bbb')
        self.assertEqual(result.name, 'bbb')
        self.assertEqual(result.another, 'ddd')

    def test_not_found(self):
        '''get_by() should return None if not found'''
        self.assertIsNone(get_by(TEST_LIST, 'name', 'not-found'))

    def test_attribute_not_found(self):
        '''get_by() should not fail if an object don't have the given attribute'''
        self.assertIsNone(get_by(TEST_LIST, 'inexistant', 'value'))


class DateRangeTest(unittest.TestCase):
    def test_parse_daterange_start_empty(self):
        self.assertIsNone(daterange_start(None))
        self.assertIsNone(daterange_start(''))

    def test_parse_daterange_end_empty(self):
        self.assertIsNone(daterange_end(None))
        self.assertIsNone(daterange_end(''))

    def test_parse_daterange_start_full(self):
        self.assertEqual(daterange_start('1984-06-07'), date(1984, 6, 7))

    def test_parse_daterange_end_full(self):
        self.assertEqual(daterange_end('1984-06-07'), date(1984, 6, 7))

    def test_parse_daterange_start_month(self):
        self.assertEqual(daterange_start('1984-06'), date(1984, 6, 1))

    def test_parse_daterange_end_month(self):
        self.assertEqual(daterange_end('1984-06'), date(1984, 6, 30))
        self.assertEqual(daterange_end('1984-07'), date(1984, 7, 31))

    def test_parse_daterange_end_month_february(self):
        self.assertEqual(daterange_end('1984-02'), date(1984, 2, 29))
        self.assertEqual(daterange_end('1985-02'), date(1985, 2, 28))

    def test_parse_daterange_start_year(self):
        self.assertEqual(daterange_start('1984'), date(1984, 1, 1))

    def test_parse_daterange_end_year(self):
        self.assertEqual(daterange_end('1984'), date(1984, 12, 31))
