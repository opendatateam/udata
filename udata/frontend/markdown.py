# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from urlparse import urlparse

import bleach
import CommonMark
import html2text
import re
from flask import current_app, Markup, request
from werkzeug.local import LocalProxy
from jinja2.filters import do_truncate, do_striptags

from udata.i18n import _

md = LocalProxy(lambda: current_app.extensions['markdown'])

EXCERPT_TOKEN = '<!--- --- -->'

RE_AUTOLINK = re.compile(
    r'^<([A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\x00-\x20]*)>',
    re.IGNORECASE)


def avoid_mailto_callback(attrs, new=False):
    """Remove completely the link containing a `mailto`."""
    if attrs[(None, 'href')].startswith('mailto:'):
        return None
    return attrs


def source_tooltip_callback(attrs, new=False):
    """
    Add a `data-tooltip` attribute with `Source` content for embeds.
    """
    attrs[(None, 'data-tooltip')] = _('Source')
    return attrs


def nofollow_callback(attrs, new=False):
    """
    Turn relative links into external ones and avoid `nofollow` for us,

    otherwise add `nofollow`.
    That callback is not splitted in order to parse the URL only once.
    """
    parsed_url = urlparse(attrs[(None, 'href')])
    if parsed_url.netloc in ('', current_app.config['SERVER_NAME']):
        attrs[(None, 'href')] = '{scheme}://{netloc}{path}'.format(
            scheme='https' if request.is_secure else 'http',
            netloc=current_app.config['SERVER_NAME'],
            path=parsed_url.path)
        return attrs
    else:
        rel = [x for x in attrs.get((None, 'rel'), '').split(' ') if x]
        if 'nofollow' not in [x.lower() for x in rel]:
            rel.append('nofollow')
        attrs[(None, 'rel')] = ' '.join(rel)
        return attrs


class UDataMarkdown(object):
    """Consistent with Flask's extensions signature."""

    def __init__(self, app, parser, renderer):
        self.parser = parser
        self.renderer = renderer
        app.jinja_env.filters.setdefault('markdown', self.__call__)

    def __call__(self, stream, source_tooltip=False, wrap=True):
        if not stream:
            return ''

        # Prepare angle bracket autolinks to avoir bleach to treat them as tag
        stream = RE_AUTOLINK.sub(r'[\g<1>](\g<1>)', stream)
        stream = bleach_clean(stream)
        # Turn markdown to HTML.
        ast = self.parser().parse(stream)
        html = self.renderer.render(ast)
        # Deal with callbacks
        callbacks = [avoid_mailto_callback, nofollow_callback]
        if source_tooltip:
            callbacks.append(source_tooltip_callback)

        # Turn string links into HTML ones *after* markdown transformation.
        html = bleach.linkify(html, skip_tags=['pre'],
                              parse_email=True, callbacks=callbacks)
        if wrap:
            html = '<div class="markdown">{0}</div>'.format(html.strip())
        # Return a `Markup` element considered as safe by Jinja.
        return Markup(html)


def bleach_clean(stream):
    """
    Sanitize malicious attempts but keep the `EXCERPT_TOKEN`.
    By default, only keeps `bleach.ALLOWED_TAGS`.
    """
    return bleach.clean(
        stream,
        tags=current_app.config['MD_ALLOWED_TAGS'],
        attributes=current_app.config['MD_ALLOWED_ATTRIBUTES'],
        styles=current_app.config['MD_ALLOWED_STYLES'],
        strip_comments=False)


def mdstrip(value, length=None, end='…'):
    '''
    Truncate and strip tags from a markdown source

    The markdown source is truncated at the excerpt if present and
    smaller than the required length. Then, all html tags are stripped.
    '''
    if not value:
        return ''
    if EXCERPT_TOKEN in value:
        value = value.split(EXCERPT_TOKEN, 1)[0]
    rendered = md(value, wrap=False)
    text = do_striptags(rendered)
    text = bleach_clean(text)
    if length and length > 0:
        text = do_truncate(None, text, length, end=end, leeway=2)
    return text


def parse_html(html):
    '''
    Parse HTML and convert it into a udata-compatible markdown string
    '''
    if not html:
        return ''
    return html2text.html2text(html.strip(), bodywidth=0).strip()


def init_app(app):
    parser = CommonMark.Parser  # Not an instance because not thread-safe(?)
    renderer = CommonMark.HtmlRenderer({'softbreak': '<br/>'})
    app.extensions['markdown'] = UDataMarkdown(app, parser, renderer)

    app.add_template_filter(mdstrip)
