import hashlib
import math
import re

import factory

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_dt
from faker import Faker
from faker.config import PROVIDERS
from faker.providers import BaseProvider
from faker.providers.lorem.la import Provider as LoremProvider
from math import ceil
from uuid import uuid4, UUID
from xml.sax.saxutils import escape


def get_by(lst, field, value):
    '''Find an object in a list given a field value'''
    for row in lst:
        if ((isinstance(row, dict) and row.get(field) == value) or
                (getattr(row, field, None) == value)):
            return row


def multi_to_dict(multi):
    '''Transform a Werkzeug multidictionnary into a flat dictionnary'''
    return dict(
        (key, value[0] if len(value) == 1 else value)
        for key, value in multi.to_dict(False).items()
    )


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')
UUID_LENGTH = 36


def camel_to_lodash(name):
    s1 = FIRST_CAP_RE.sub(r'\1_\2', name)
    return ALL_CAP_RE.sub(r'\1_\2', s1).lower()


class Paginable(object):
    '''
    A simple helper mixin for pagination
    '''
    @property
    def pages(self):
        if self.page_size:
            return int(ceil(self.total / float(self.page_size)))
        else:
            return 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def page_start(self):
        if self.page_size is not None:
            return (self.page - 1) * self.page_size + 1
        else:
            return 1

    @property
    def page_end(self):
        return min(self.total, self.page_size * self.page)

    def iter_pages(self, left_edge=2, left_current=2, right_current=5,
                   right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                    (num > self.page - left_current - 1 and
                        num < self.page + right_current) or
                    num > self.pages - right_edge):
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


def daterange_start(value):
    '''Parse a date range start boundary'''
    if not value:
        return None
    elif isinstance(value, datetime):
        return value.date()
    elif isinstance(value, date):
        return value

    result = parse_dt(value).date()
    dashes = value.count('-')

    if dashes >= 2:
        return result
    elif dashes == 1:
        # Year/Month only
        return result.replace(day=1)
    else:
        # Year only
        return result.replace(day=1, month=1)


def daterange_end(value):
    '''Parse a date range end boundary'''
    if not value:
        return None
    elif isinstance(value, datetime):
        return value.date()
    elif isinstance(value, date):
        return value

    result = parse_dt(value).date()
    dashes = value.count('-')

    if dashes >= 2:
        # Full date
        return result
    elif dashes == 1:
        # Year/Month
        return result + relativedelta(months=+1, days=-1, day=1)
    else:
        # Year only
        return result.replace(month=12, day=31)


def to_iso(dt):
    '''
    Format a date or datetime into an ISO-8601 string

    Support dates before 1900.
    '''
    if isinstance(dt, datetime):
        return to_iso_datetime(dt)
    elif isinstance(dt, date):
        return to_iso_date(dt)


def to_iso_date(dt):
    '''
    Format a date or datetime into an ISO-8601 date string.

    Support dates before 1900.
    '''
    if dt:
        return '{dt.year:02d}-{dt.month:02d}-{dt.day:02d}'.format(dt=dt)


def to_iso_datetime(dt):
    '''
    Format a date or datetime into an ISO-8601 datetime string.

    Time is set to 00:00:00 for dates.

    Support dates before 1900.
    '''
    if dt:
        date_str = to_iso_date(dt)
        time_str = '{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}'.format(
            dt=dt) if isinstance(dt, datetime) else '00:00:00'
        return 'T'.join((date_str, time_str))


def to_bool(value):
    '''
    Transform a value into a boolean with the following rules:

    - a boolean is returned untouched
    - a string value should match any casinf of 'true' to be True
    - an integer should be superior to zero to be True
    - all other values are False
    '''
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower() == 'true' or value.lower() == 't'
    elif isinstance(value, int):
        return value > 0
    else:
        return False


def clean_string(value):
    '''
    Clean an user input string (Prevent it from containing XSS)
    '''
    return escape(value)


def not_none_dict(d):
    '''Filter out None values from a dict'''
    return {k: v for k, v in d.items() if v is not None}


def hash_url(url):
    '''Hash an URL to make it indexable'''
    return hashlib.sha1(url.encode('utf-8')).hexdigest() if url else None


def recursive_get(obj, key):
    '''
    Get an attribute or a key recursively.

    :param obj: The object to fetch attribute or key on
    :type obj: object|dict
    :param key: Either a string in dotted-notation ar an array of string
    :type key: string|list|tuple
    '''
    if not obj or not key:
        return
    parts = key.split('.') if isinstance(key, str) else key
    key = parts.pop(0)
    if isinstance(obj, dict):
        value = obj.get(key, None)
    else:
        value = getattr(obj, key, None)
    return recursive_get(value, parts) if parts else value


def unique_string(length=UUID_LENGTH):
    '''Generate a unique string'''
    # We need a string at least as long as length
    string = str(uuid4()) * int(math.ceil(length / float(UUID_LENGTH)))
    return string[:length] if length else string


def is_uuid(uuid_string, version=4):
    try:
        # If uuid_string is a valid hex code but not a valid uuid,
        # UUID() will still make a valide uuid out of it.
        # to prevent this, we check the genuine version (without dashes)
        # with the generated hex code. They should be similar.
        uid = UUID(uuid_string, version=version)
        return uid.hex == uuid_string.replace('-', '')
    except ValueError:
        return False


# This is the default providers list
# We remove the lorum one to replace it
# with a unicode enabled one below
PROVIDERS.remove('faker.providers.lorem')

faker = Faker('fr_FR')  # Use a unicode/utf-8 based locale


def faker_provider(provider):
    faker.add_provider(provider)
    factory.Faker.add_provider(provider)
    return provider


@faker_provider
class UDataProvider(BaseProvider):
    '''
    A Faker provider for udata missing requirements.

    Might be conributed to upstream Faker project
    '''
    def unique_string(self, length=UUID_LENGTH):
        '''Generate a unique string'''
        return unique_string(length)


@faker_provider  # Replace the default lorem provider with a unicode one
class UnicodeLoremProvider(LoremProvider):
    '''A Lorem provider that forces unicode in words'''
    word_list = [w + 'é' for w in LoremProvider.word_list]


def safe_unicode(string):
    '''Safely transform any object into utf8 decoded str'''
    return string.decode('utf8') if isinstance(string, bytes) else str(string)
