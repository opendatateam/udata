# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from datetime import date
from calendar import monthrange
from math import ceil


def get_by(lst, field, value):
    '''Find an object in a list given a field value'''
    for row in lst:
        if (isinstance(row, dict) and row.get(field) == value) or (getattr(row, field, None) == value):
            return row


def multi_to_dict(multi):
    '''Transform a Werkzeug multidictionnary into a flat dictionnary'''
    return dict(
        (key, value[0] if len(value) == 1 else value)
        for key, value in multi.to_dict(False).items()
    )


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')


def camel_to_lodash(name):
    s1 = FIRST_CAP_RE.sub(r'\1_\2', name)
    return ALL_CAP_RE.sub(r'\1_\2', s1).lower()


class Paginable(object):
    '''
    A simple helper mixin for pagination
    '''
    @property
    def pages(self):
        return int(ceil(self.total / float(self.page_size)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def page_start(self):
        return (self.page - 1) * self.page_size + 1

    @property
    def page_end(self):
        return min(self.total, self.page_size * self.page)

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                (num > self.page - left_current - 1 and num < self.page + right_current) or \
                num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class Paginator(Paginable):
    '''A simple paginable implementation'''
    def __init__(self, page, page_size, total):
        self.page = page
        self.page_size = page_size
        self.total = total


def daterange_start(string):
    '''Parse a date range start boundary'''
    if not string:
        return None
    parts = string.split('-')

    if len(parts) == 3:
        return date(*(int(part) for part in parts))
    elif len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    else:
        return date(int(parts[0]), 1, 1)


def daterange_end(string):
    '''Parse a date range end boundary'''
    if not string:
        return None
    parts = string.split('-')

    if len(parts) == 3:
        return date(*(int(part) for part in parts))
    elif len(parts) == 2:
        year, month = int(parts[0]), int(parts[1])
        _, end_of_month = monthrange(year, month)
        return date(year, month, end_of_month)
    else:
        return date(int(parts[0]), 12, 31)
