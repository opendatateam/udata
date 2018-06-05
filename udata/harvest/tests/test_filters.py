# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import pytest

from voluptuous import Invalid

from udata.harvest import filters

log = logging.getLogger(__name__)


class FiltersTest:
    def test_boolean(self):
        true_values = ('1', 'on', 't', 'TRUE', 'true', 'y', 'yes', '  1  ',
                       '  tRuE  ', True, 1, 2, -1)
        false_values = ('0', 'f', 'FALSE', 'false', 'n', 'no', 'off', '  0  ',
                        '  f  ', False, 0)
        none_values = ('', '   ', None)

        for value in true_values:
            assert filters.boolean(value)

        for value in false_values:
            assert filters.boolean(value) is False

        for value in none_values:
            assert filters.boolean(value) is None

        with pytest.raises(Invalid):
            filters.boolean('vrai')

    def test_empty_none(self):
        empty_values = 0, '', [], {}
        non_empty_values = 'hello', '  hello  '

        for value in empty_values:
            assert filters.empty_none(value) is None

        for value in non_empty_values:
            assert filters.empty_none(value) == value

    def test_strip(self):
        assert filters.strip('  hello   ') == 'hello'
        assert filters.strip('    ') is None

    def test_line_endings(self):
        result = filters.line_endings('hello\r\nworld!\r ')
        assert result == 'hello\nworld!\n '

    def test_hash(self):
        hashes = {
            'md5': 'bd8668597bfba2d1843441d7199bea65',
            'sha1': 'f2f0249827f501286b4713683e526d541d2cc7e2',
            'sha256': ('c4373e1d81eb44882bf9ff539d0e5f'
                       'faf03a114abf9306591117d781966268f9')
        }

        for type, value in hashes.items():
            assert filters.hash(value) == {'type': type, 'value': value}

    def test_unknown_hash(self):
        assert filters.hash('xxxx') is None
        assert filters.hash(None) is None


class IsUrlFilterTest:
    def test_valid_url_with_defaults(self):
        f = filters.is_url()
        assert f('https://somewhere.com/path') == 'https://somewhere.com/path'

    def test_allowed_scheme_not_allowed(self):
        f = filters.is_url()
        with pytest.raises(Invalid):
            f('not-allowed://somewhere.com')

    def test_valid_url_with_default_scheme(self):
        f = filters.is_url()
        assert f('somewhere.com/path') == 'http://somewhere.com/path'
