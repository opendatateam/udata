# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import calendar
import logging
import pkg_resources

from datetime import date, datetime
from time import time
from urlparse import urlsplit, urlunsplit

from babel.numbers import format_number as format_number_babel
from flask import g, url_for, request, current_app, json
from jinja2 import Markup
from werkzeug import url_decode, url_encode

from . import front

from udata.models import db
from udata.i18n import format_date, _, pgettext, get_current_locale
from udata.utils import camel_to_lodash


log = logging.getLogger(__name__)


@front.app_template_global()
def udata_version():
    return pkg_resources.get_distribution('udata').version


@front.app_template_global()
def now():
    return datetime.now()


@front.app_template_global(name='static')
def static_global(filename, _burst=True, **kwargs):
    if current_app.config['DEBUG'] or current_app.config['TESTING']:
        burst = time()
    else:
        burst = udata_version()
    if _burst:
        kwargs['_'] = burst
    return url_for('static', filename=filename, **kwargs)


@front.app_template_global(name='form_grid')
def form_grid(specs):
    if not specs:
        return None
    label_sizes, control_sizes, offset_sizes = [], [], []
    for spec in specs.split(','):
        label_sizes.append('col-{0}'.format(spec))
        size, col = spec.split('-')
        offset_sizes.append('col-{0}-offset-{1}'.format(size, col))
        col = 12 - int(col)
        control_sizes.append('col-{0}-{1}'.format(size, col))
    return {
        'label': ' '.join(label_sizes),
        'control': ' '.join(control_sizes),
        'offset': ' '.join(offset_sizes),
    }


@front.app_template_global()
@front.app_template_filter()
def url_rewrite(url=None, **kwargs):
    scheme, netloc, path, query, fragments = urlsplit(url or request.url)
    params = url_decode(query)
    for key, value in kwargs.items():
        params.setlist(key,
                       value if isinstance(value, (list, tuple)) else [value])
    return Markup(urlunsplit((scheme, netloc, path, url_encode(params),
                  fragments)))


@front.app_template_global()
@front.app_template_filter()
def url_add(url=None, **kwargs):
    scheme, netloc, path, query, fragments = urlsplit(url or request.url)
    params = url_decode(query)
    for key, value in kwargs.items():
        if value not in params.getlist(key):
            params.add(key, value)
    return Markup(urlunsplit((scheme, netloc, path, url_encode(params),
                              fragments)))


@front.app_template_global()
@front.app_template_filter()
def url_del(url=None, *args, **kwargs):
    scheme, netloc, path, query, fragments = urlsplit(url or request.url)
    params = url_decode(query)
    for key in args:
        params.poplist(key)
    for key, value in kwargs.items():
        lst = params.poplist(key)
        if unicode(value) in lst:
            lst.remove(unicode(value))
        params.setlist(key, lst)
    return Markup(urlunsplit((scheme, netloc, path, url_encode(params),
                              fragments)))


@front.app_template_global()
def in_url(*args, **kwargs):
    scheme, netloc, path, query, fragments = urlsplit(request.url)
    params = url_decode(query)
    return (
        all(arg in params for arg in args) and
        all(key in params and params[key] == value
            for key, value in kwargs.items())
    )


@front.app_template_filter()
def placeholder(url, name='default', external=False):
    return url or url_for(
        'static',
        filename='img/placeholders/{0}.png'.format(name),
        _external=external)


@front.app_template_filter()
def obfuscate(email):
    """Poor-man obfuscation, don't forget the |safe filter after it."""
    return email.replace('@', '%40').replace('.', '&#46;')


@front.app_template_filter()
@front.app_template_global()
def avatar_url(obj, size):
    if hasattr(obj, 'avatar') and obj.avatar:
        return obj.avatar(size)
    elif hasattr(obj, 'logo') and obj.logo:
        return obj.logo(size)
    else:
        return placeholder(None, 'user')


@front.app_template_global()
@front.app_template_filter()
def owner_avatar_url(obj, size=32):
    if hasattr(obj, 'organization') and obj.organization:
        return (obj.organization.logo(size)
                if obj.organization.logo
                else placeholder(None, 'organization'))
    elif hasattr(obj, 'owner') and obj.owner:
        return avatar_url(obj.owner, size)
    return placeholder(None, 'user')


@front.app_template_global()
@front.app_template_filter()
def owner_url(obj):
    if hasattr(obj, 'organization') and obj.organization:
        return url_for('organizations.show', org=obj.organization)
    elif hasattr(obj, 'owner') and obj.owner:
        return url_for('users.show', user=obj.owner)
    return ''


@front.app_template_filter()
@front.app_template_global()
def avatar(user, size, classes=''):
    markup = '''
        <a class="avatar {classes}" href="{url}" title="{title}">
            <img src="{avatar_url}" class="avatar" alt="{title}"
            width="{size}" height="{size}"/>
        </a>
    '''.format(
        title=getattr(user, 'fullname', _('Anonymous user')),
        url=(url_for('users.show', user=user)
             if user and getattr(user, 'id', None) else '#'),
        size=size,
        avatar_url=avatar_url(user, size),
        classes=classes
    )
    return Markup(markup)


@front.app_template_global()
@front.app_template_filter()
def owner_avatar(obj, size=32):
    markup = '''
        <a class="avatar" href="{url}" title="{title}">
            <img src="{avatar_url}" class="avatar" alt="{title}"
            width="{size}" height="{size}"/>
        </a>
    '''
    return Markup(markup.format(
        title=owner_name(obj),
        url=owner_url(obj),
        size=size,
        avatar_url=owner_avatar_url(obj, size),
    ))


@front.app_template_global()
@front.app_template_filter()
def owner_name(obj):
    if hasattr(obj, 'organization') and obj.organization:
        return obj.organization.name
    elif hasattr(obj, 'owner') and obj.owner:
        return obj.owner.fullname
    return ''


@front.app_template_global()
@front.app_template_filter()
def isodate(value, format='short'):
    dt = date(*map(int, value.split('-')))
    return format_date(dt, format)


@front.app_template_global()
@front.app_template_filter()
def isoformat(value):
    return value.isoformat()


front.add_app_template_filter(camel_to_lodash)


@front.app_template_global()
@front.app_template_filter()
def tooltip_ellipsis(source, length=0):
    ''' return the plain text representation of markdown encoded text.  That
    is the texted without any html tags.  If ``length`` is 0 then it
    will not be truncated.'''
    try:
        length = int(length)
    except ValueError:  # invalid literal for int()
        return source  # Fail silently.
    ellipsis = '<a href v-tooltip title="{0}">...</a>'.format(source)
    return Markup((source[:length] + ellipsis)
                  if len(source) > length and length > 0 else source)


@front.app_template_global()
@front.app_template_filter()
def percent(value, max_value, over=False):
    percent = (value or 0) * 100. / max_value
    return percent if over else min(percent, 100)


def is_first_month_day(date):
    return date.day == 1


def is_last_month_day(date):
    _, last_day = calendar.monthrange(date.year, date.month)
    return date.day == last_day


def is_first_year_day(date):
    return date.day == 1 and date.month == 1


def is_last_year_day(date):
    return date.month == 12 and is_last_month_day(date)


def short_month(date):
    return format_date(date, pgettext('month-format', 'yyyy/MM'))


def short_day(date):
    return format_date(date, pgettext('day-format', 'yyyy/MM/dd'))


@front.app_template_global()
@front.app_template_filter()
def daterange(value):
    '''Display a date range in the shorter possible maner.'''
    if not isinstance(value, db.DateRange):
        raise ValueError('daterange only accept db.DateRange as parameter')
    delta = value.end - value.start
    start, end = None, None
    if is_first_year_day(value.start) and is_last_year_day(value.end):
        start = value.start.year
        if delta.days > 365:
            end = value.end.year
    elif is_first_month_day(value.start) and is_last_month_day(value.end):
        start = short_month(value.start)
        if delta.days > 31:
            end = short_month(value.end)
    else:
        start = short_day(value.start)
        if value.start != value.end:
            end = short_day(value.end)
    return _('%(start)s to %(end)s', start=start, end=end) if end else start


@front.app_template_filter()
@front.app_template_global()
def ficon(value):
    '''A simple helper for font icon class'''
    return ('fa {0}'.format(value)
            if value.startswith('fa')
            else 'glyphicon glyphicon-{0}'.format(value))


@front.app_template_filter()
@front.app_template_global()
def i18n_alternate_links():
    """Render the <link rel="alternate" hreflang />

    if page is in a I18nBlueprint
    """
    if (not request.endpoint or
            not current_app.url_map.is_endpoint_expecting(request.endpoint,
                                                          'lang_code')):
        return Markup('')

    try:
        LINK_PATTERN = (
            '<link rel="alternate" href="{url}" hreflang="{lang}" />')
        links = []
        current_lang = get_current_locale().language

        params = {}
        if request.args:
            params.update(request.args)
        if request.view_args:
            params.update(request.view_args)

        for lang in current_app.config['LANGUAGES']:
            if lang != current_lang:
                url = url_for(request.endpoint, lang_code=lang, **params)
                links.append(LINK_PATTERN.format(url=url, lang=lang))
        return Markup(''.join(links))
    except:
        # Never fails
        return Markup('')


@front.app_template_filter()
@front.app_template_global()
def to_json(data):
    '''Convert data to JSON, you may have to use |safe after it.'''
    if not data:
        return Markup('')
    return json.dumps(data)


@front.app_template_filter()
@front.app_template_global()
def format_number(number):
    '''A locale aware formatter.'''
    return format_number_babel(number, locale=g.lang_code)
