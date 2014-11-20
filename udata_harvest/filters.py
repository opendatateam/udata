# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import dateutil.parser
import slugify

from voluptuous import Invalid, MultipleInvalid


def boolean(value):
    '''
    Convert the content of a string (or a number) to a boolean.
    Do nothing when input value is already a boolean.

    This filter accepts usual values for ``True`` and ``False``: "0", "f", "false", "n", etc.
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
    if not '@' in value:
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
    return slugify.slugify(value, separator='-')


def taglist(value):
    return [slugify.slugify(t, separator='-') for t in value.split(',')]


def empty_none(value):
    '''Replace falsy values with None

    >>> cleanup_empty(0)
    None
    >>> cleanup_empty('')
    None
    >>> cleanup_empty([])
    None
    >>> cleanup_empty({})
    None
    >>> cleanup_empty(u'hello world')
    (u'hello world', None)
    >>> cleanup_empty(u'   hello world   ')
    (u'   hello world   ', None)
    '''
    return value if value else None


def strip(value):
    '''Strip spaces from a string and remove it when empty.

    >>> cleanup_line(u'   Hello world!   ')
    (u'Hello world!', None)
    >>> cleanup_line('   ')
    (None, None)
    >>> cleanup_line(None)
    (None, None)
    '''
    return empty_none(value.strip())


def line_endings(value):
    """Replaces CR + LF or CR to LF in a string, then strip spaces and remove it when empty.

    >>> cleanup_text(u'   Hello\\r\\n world!\\r   ')
    (u'Hello\\n world!', None)
    >>> cleanup_text('   ')
    (None, None)
    >>> cleanup_text(None)
    (None, None)
    """
    return value.replace(u'\r\n', u'\n').replace(u'\r', u'\n')


def normalize_string(value):
    return strip(line_endings(value))


def is_url(add_prefix='http://', full=False, remove_fragment=False, schemes=(u'http', u'https')):
    """Return a converter that converts a clean string to an URL.

    .. note:: For a converter that doesn't require a clean string, see :func:`str_to_url`.

    >>> i_url()(u'http://packages.python.org/Biryani/')
    (u'http://packages.python.org/Biryani/', None)
    >>> clean_str_to_url(full = True)(u'packages.python.org/Biryani/')
    (u'http://packages.python.org/Biryani/', None)
    >>> clean_str_to_url()(u'/Biryani/presentation.html#tutorial')
    (u'/Biryani/presentation.html#tutorial', None)
    >>> clean_str_to_url(full = True)(u'/Biryani/presentation.html#tutorial')
    (u'/Biryani/presentation.html#tutorial', u'URL must be complete')
    >>> clean_str_to_url(remove_fragment = True)(u'http://packages.python.org/Biryani/presentation.html#tutorial')
    (u'http://packages.python.org/Biryani/presentation.html', None)
    """
    def converter(value):
        if value is None:
            return value
        import urlparse
        split_url = list(urlparse.urlsplit(value))
        if full and add_prefix and not split_url[0] and not split_url[1] and split_url[2] \
                and not split_url[2].startswith(u'/'):
            split_url = list(urlparse.urlsplit(add_prefix + value))
        scheme = split_url[0]
        if scheme != scheme.lower():
            split_url[0] = scheme = scheme.lower()
        if full and not scheme:
            raise Invalid('URL must be complete')
        if scheme and schemes is not None and scheme not in schemes:
            raise Invalid('Scheme must belong to {0}').format(sorted(schemes))
        network_location = split_url[1]
        if network_location != network_location.lower():
            split_url[1] = network_location = network_location.lower()
        if scheme in ('http', 'https') and not split_url[2]:
            # By convention a full HTTP URL must always have at least a "/" in its path.
            split_url[2] = '/'
        if remove_fragment and split_url[4]:
            split_url[4] = ''
        return unicode(urlparse.urlunsplit(split_url))
    return converter
