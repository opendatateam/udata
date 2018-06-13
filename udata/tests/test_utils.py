# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime

from udata.utils import (
    get_by, daterange_start, daterange_end, to_bool, to_iso, to_iso_date,
    to_iso_datetime, recursive_get, safe_unicode
)

TEST_LIST = [
    {'name': 'aaa', 'other': 'bbb'},
    {'name': 'bbb', 'another': 'ddd'},
    {'name': 'ccc', 'other': 'bbb'},
]


class ObjDict(object):
    def __init__(self, d):
        self.__dict__.update(d)


class GetByFieldTest:
    def test_find_dict(self):
        '''get_by() should find a dictionnary in list'''
        result = get_by(TEST_LIST, 'name', 'bbb')
        assert result == {'name': 'bbb', 'another': 'ddd'}

    def test_find_object(self):
        '''get_by() should find an object in list'''
        obj_lst = [ObjDict(d) for d in TEST_LIST]
        result = get_by(obj_lst, 'name', 'bbb')
        assert result.name == 'bbb'
        assert result.another == 'ddd'

    def test_not_found(self):
        '''get_by() should return None if not found'''
        assert get_by(TEST_LIST, 'name', 'not-found') is None

    def test_attribute_not_found(self):
        '''get_by() should not fail if an object don't have the given attr'''
        assert get_by(TEST_LIST, 'inexistant', 'value') is None


class DateRangeTest:
    def test_parse_daterange_start_empty(self):
        assert daterange_start(None) is None
        assert daterange_start('') is None

    def test_parse_daterange_end_empty(self):
        assert daterange_end(None) is None
        assert daterange_end('') is None

    def test_parse_daterange_start_date(self):
        today = date.today()
        assert daterange_start(today) == today

    def test_parse_daterange_end_date(self):
        today = date.today()
        assert daterange_end(today) == today

    def test_parse_daterange_start_datetime(self):
        now = datetime.now()
        assert daterange_start(now) == now.date()

    def test_parse_daterange_end_datetime(self):
        now = datetime.now()
        assert daterange_end(now) == now.date()

    def test_parse_daterange_start_full_iso(self):
        assert daterange_start('1984-06-07T00:00:00+00:00') == date(1984, 6, 7)

    def test_parse_daterange_end_full_iso(self):
        assert daterange_end('1984-06-07T00:00:00+00:00') == date(1984, 6, 7)

    def test_parse_daterange_start_full(self):
        assert daterange_start('1984-06-07') == date(1984, 6, 7)

    def test_parse_daterange_end_full(self):
        assert daterange_end('1984-06-07') == date(1984, 6, 7)

    def test_parse_daterange_start_month(self):
        assert daterange_start('1984-06') == date(1984, 6, 1)

    def test_parse_daterange_end_month(self):
        assert daterange_end('1984-06') == date(1984, 6, 30)
        assert daterange_end('1984-07') == date(1984, 7, 31)

    def test_parse_daterange_end_month_february(self):
        assert daterange_end('1984-02') == date(1984, 2, 29)
        assert daterange_end('1985-02') == date(1985, 2, 28)

    def test_parse_daterange_start_year(self):
        assert daterange_start('1984') == date(1984, 1, 1)

    def test_parse_daterange_end_year(self):
        assert daterange_end('1984') == date(1984, 12, 31)

    def test_parse_before_1900(self):
        assert daterange_start('1860') == date(1860, 1, 1)
        assert daterange_end('1860') == date(1860, 12, 31)


class ToBoolTest:
    def test_bool_values(self):
        assert to_bool(True) is True
        assert to_bool(False) is False

    def test_string_values(self):
        assert to_bool('True') is True
        assert to_bool('true') is True
        assert to_bool('False') is False
        assert to_bool('false') is False
        assert to_bool('bla') is False
        assert to_bool('T') is True
        assert to_bool('F') is False
        assert to_bool('t') is True
        assert to_bool('f') is False

    def test_int_values(self):
        assert to_bool(0) is False
        assert to_bool(-1) is False
        assert to_bool(1) is True
        assert to_bool(10) is True


class ToIsoTest:
    def test_to_iso_date_emtpy(self):
        assert to_iso_date(None) is None

    def test_to_iso_date_with_datetime(self):
        assert to_iso_date(datetime(1984, 2, 29, 1, 2, 3)) == '1984-02-29'

    def test_to_iso_date_with_date(self):
        assert to_iso_date(date(1984, 2, 29)) == '1984-02-29'

    def test_to_iso_date_before_1900(self):
        assert to_iso_date(date(1884, 2, 29)) == '1884-02-29'

    def test_to_iso_datetime_emtpy(self):
        assert to_iso_datetime(None) is None

    def test_to_iso_datetime_with_datetime(self):
        result = to_iso_datetime(datetime(1984, 2, 29, 1, 2, 3))
        assert result == '1984-02-29T01:02:03'

    def test_to_iso_datetime_with_date(self):
        assert to_iso_datetime(date(1984, 2, 29)) == '1984-02-29T00:00:00'

    def test_to_iso_datetime_before_1900(self):
        assert to_iso_datetime(date(1884, 2, 29)) == '1884-02-29T00:00:00'

    def test_to_iso_emtpy(self):
        assert to_iso(None) is None

    def test_to_iso_with_datetime(self):
        assert to_iso(datetime(1984, 2, 29, 1, 2, 3)) == '1984-02-29T01:02:03'

    def test_to_iso_with_date(self):
        assert to_iso(date(1984, 2, 29)) == '1984-02-29'


class RecursiveGetTest:
    def test_get_root_attribute(self):
        class Tester(object):
            attr = 'value'

        tester = Tester()
        assert recursive_get(tester, 'attr') == 'value'

    def test_get_root_key(self):
        tester = {'key': 'value'}
        assert recursive_get(tester, 'key') == 'value'

    def test_get_nested_attribute(self):
        class Nested(object):
            attr = 'value'

        class Tester(object):
            def __init__(self):
                self.nested = Nested()

        tester = Tester()
        assert recursive_get(tester, 'nested.attr') == 'value'

    def test_get_nested_key(self):
        tester = {'nested': {'key': 'value'}}
        assert recursive_get(tester, 'nested.key') == 'value'

    def test_attr_not_found(self):
        class Tester(object):
            pass

        tester = Tester()
        assert recursive_get(tester, 'attr') is None

    def test_key_not_found(self):
        tester = {'key': 'value'}
        assert recursive_get(tester, 'not-found') is None

    def test_nested_attribute_not_found(self):
        class Nested(object):
            attr = 'value'

        class Tester(object):
            def __init__(self):
                self.nested = Nested()

        tester = Tester()
        assert recursive_get(tester, 'nested.not_found') is None

    def test_nested_key_not_found(self):
        tester = {'nested': {'key': 'value'}}
        assert recursive_get(tester, 'nested.not_found') is None

    def test_get_on_none(self):
        assert recursive_get(None, 'attr') is None

    def test_get_key_none(self):
        tester = {'key': 'value'}
        assert recursive_get(tester, None) is None
        assert recursive_get(tester, '') is None


class SafeUnicodeTest(object):
    def test_unicode_is_encoded(self):
        assert safe_unicode('ééé') == 'ééé'.encode('utf8')

    def test_bytes_stays_bytes(self):
        assert safe_unicode(b'xxx') == b'xxx'

    def test_object_to_string(self):
        assert safe_unicode({}) == b'{}'

    def test_unicode_to_string(self):
        assert safe_unicode(ValueError('é')) == 'é'.encode('utf8')
