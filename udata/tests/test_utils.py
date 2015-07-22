# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from datetime import date, datetime

from udata.utils import (
    get_by, daterange_start, daterange_end, to_bool, to_iso, to_iso_date,
    to_iso_datetime
)

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
        '''get_by() should not fail if an object don't have the given attr'''
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

    def test_parse_before_1900(self):
        self.assertEqual(daterange_start('1860'), date(1860, 1, 1))
        self.assertEqual(daterange_end('1860'), date(1860, 12, 31))


class ToBoolTest(unittest.TestCase):
    def test_bool_values(self):
        self.assertEqual(to_bool(True), True)
        self.assertEqual(to_bool(False), False)

    def test_string_values(self):
        self.assertEqual(to_bool('True'), True)
        self.assertEqual(to_bool('true'), True)
        self.assertEqual(to_bool('False'), False)
        self.assertEqual(to_bool('false'), False)
        self.assertEqual(to_bool('bla'), False)

    def test_int_values(self):
        self.assertEqual(to_bool(0), False)
        self.assertEqual(to_bool(-1), False)
        self.assertEqual(to_bool(1), True)
        self.assertEqual(to_bool(10), True)


class ToIsoTest(unittest.TestCase):
    def test_to_iso_date_emtpy(self):
        self.assertEqual(to_iso_date(None), None)

    def test_to_iso_date_with_datetime(self):
        self.assertEqual(to_iso_date(datetime(1984, 2, 29, 1, 2, 3)),
                         '1984-02-29')

    def test_to_iso_date_with_date(self):
        self.assertEqual(to_iso_date(date(1984, 2, 29)), '1984-02-29')

    def test_to_iso_date_before_1900(self):
        self.assertEqual(to_iso_date(date(1884, 2, 29)), '1884-02-29')

    def test_to_iso_datetime_emtpy(self):
        self.assertEqual(to_iso_datetime(None), None)

    def test_to_iso_datetime_with_datetime(self):
        self.assertEqual(to_iso_datetime(datetime(1984, 2, 29, 1, 2, 3)),
                         '1984-02-29T01:02:03')

    def test_to_iso_datetime_with_date(self):
        self.assertEqual(to_iso_datetime(date(1984, 2, 29)),
                         '1984-02-29T00:00:00')

    def test_to_iso_datetime_before_1900(self):
        self.assertEqual(to_iso_datetime(date(1884, 2, 29)),
                         '1884-02-29T00:00:00')

    def test_to_iso_emtpy(self):
        self.assertEqual(to_iso(None), None)

    def test_to_iso_with_datetime(self):
        self.assertEqual(to_iso(datetime(1984, 2, 29, 1, 2, 3)),
                         '1984-02-29T01:02:03')

    def test_to_iso_with_date(self):
        self.assertEqual(to_iso(date(1984, 2, 29)), '1984-02-29')
