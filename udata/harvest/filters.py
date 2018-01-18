# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import urlparse

import dateutil.parser

from voluptuous import Invalid

from udata import tags


def boolean(value):
    '''
    Convert the content of a string (or a number) to a boolean.
    Do nothing when input value is already a boolean.

    This filter accepts usual values for ``True`` and ``False``:
    "0", "f", "false", "n", etc.
    '''
    if value is None or isinstance(value, bool):
        return value

    try:
        return bool(int(value))
    except ValueError:
        lower_value = value.strip().lower()
        if not lower_value:
            return None
        if lower_value in ('f', 'false', 'n', 'no', 'off'):
            return False
        if lower_value in ('on', 't', 'true', 'y', 'yes'):
            return True
        raise Invalid('Unable to parse boolean {0}'.format(value))


def to_date(value):
    '''Parse a date'''
    return dateutil.parser.parse(value).date()


def email(value):
    '''Validate an email'''
    if '@' not in value:
        raise Invalid('This email is invalid.')
    return value


def force_list(value):
    '''
    Ensure single elements are wrapped into list
    '''
    if not isinstance(value, (list, tuple)):
        return [value]
    return value


def slug(value):
    return tags.slug(value)


def normalize_tag(value):
    return tags.normalize(value)


def taglist(value):
    return tags.tags_list(value)


def empty_none(value):
    '''Replace falsy values with None'''
    return value if value else None


def strip(value):
    '''Strip spaces from a string and remove it when empty.'''
    return empty_none(value.strip())


def line_endings(value):
    """Replaces CR + LF or CR to LF in a string,
    then strip spaces and remove it when empty.
    """
    return value.replace('\r\n', '\n').replace('\r', '\n')


def normalize_string(value):
    return strip(line_endings(value))


def is_url(add_prefix='http://', full=False, remove_fragment=False,
           schemes=('http', 'https')):
    """Return a converter that converts a clean string to an URL."""
    def converter(value):
        if value is None:
            return value
        split_url = list(urlparse.urlsplit(value))
        if full and add_prefix \
                and not all((split_url[0], split_url[1], split_url[2])) \
                and not split_url[2].startswith('/'):
            split_url = list(urlparse.urlsplit(add_prefix + value))
        scheme = split_url[0]
        if scheme != scheme.lower():
            split_url[0] = scheme = scheme.lower()
        if full and not scheme:
            raise Invalid('URL must be complete')
        if scheme and schemes is not None and scheme not in schemes:
            raise Invalid('Scheme must belong to {0}'.format(sorted(schemes)))
        network_location = split_url[1]
        if network_location != network_location.lower():
            split_url[1] = network_location = network_location.lower()
        if scheme in ('http', 'https') and not split_url[2]:
            # By convention a full HTTP URL must always have
            # at least a "/" in its path.
            split_url[2] = '/'
        if remove_fragment and split_url[4]:
            split_url[4] = ''
        return unicode(urlparse.urlunsplit(split_url))
    return converter


def hash(value):
    '''Detect an hash type'''
    if not value:
        return
    elif len(value) == 32:
        type = 'md5'
    elif len(value) == 40:
        type = 'sha1'
    elif len(value) == 64:
        type = 'sha256'
    else:
        return None
    return {'type': type, 'value': value}
