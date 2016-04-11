# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from urlparse import urlparse

import bleach
import CommonMark
from html5lib.sanitizer import HTMLSanitizer
from flask import current_app, Markup
from werkzeug.local import LocalProxy
from jinja2.filters import do_truncate, do_striptags

from udata.i18n import _

md = LocalProxy(lambda: current_app.extensions['markdown'])

EXCERPT_TOKEN = '<!--- --- -->'


def avoid_mailto_callback(attrs, new=False):
    """Remove completely the link containing a `mailto`."""
    if attrs['href'].startswith('mailto:'):
        return None
    return attrs


def source_tooltip_callback(attrs, new=False):
    """
    Add a `data-tooltip` attribute with `Source` content for embeds.
    """
    attrs['data-tooltip'] = _('Source')
    return attrs


def nofollow_callback(attrs, new=False):
    """
    Turn relative links into external ones and avoid `nofollow` for us,

    otherwise add `nofollow`.
    That callback is not splitted in order to parse the URL only once.
    """
    parsed_url = urlparse(attrs['href'])
    if parsed_url.netloc in ('', current_app.config['SERVER_NAME']):
        attrs['href'] = '{scheme}://{netloc}{path}'.format(
            scheme=current_app.config['USE_SSL'] and 'https' or 'http',
            netloc=current_app.config['SERVER_NAME'],
            path=parsed_url.path)
        return attrs
    else:
        rel = [x for x in attrs.get('rel', '').split(' ') if x]
        if 'nofollow' not in [x.lower() for x in rel]:
            rel.append('nofollow')
        attrs['rel'] = ' '.join(rel)
        return attrs


class KeepTokenSanitizer(HTMLSanitizer):
    """Keep the `EXCERPT_TOKEN` with bleach."""

    def sanitize_token(self, token):
        return token


class UDataMarkdown(object):
    """Consistent with Flask's extensions signature."""

    def __init__(self, app, parser, renderer):
        self.parser = parser
        self.renderer = renderer
        app.jinja_env.filters.setdefault('markdown', self.__call__)

    def __call__(self, stream, source_tooltip=False):
        if not stream:
            return ''
        # Sanitize malicious attempts but keep the `EXCERPT_TOKEN`.
        # By default, only keeps `bleach.ALLOWED_TAGS`.
        stream = bleach.clean(
            stream,
            tags=current_app.config['MD_ALLOWED_TAGS'],
            attributes=current_app.config['MD_ALLOWED_ATTRIBUTES'],
            styles=current_app.config['MD_ALLOWED_STYLES'],
            strip_comments=False)
        # Turn markdown to HTML.
        ast = self.parser().parse(stream)
        html = self.renderer.render(ast)
        # Deal with callbacks
        callbacks = [avoid_mailto_callback, nofollow_callback]
        if source_tooltip:
            callbacks.append(source_tooltip_callback)

        # Turn string links into HTML ones *after* markdown transformation.
        html = bleach.linkify(
            html, tokenizer=KeepTokenSanitizer,
            skip_pre=True, parse_email=True, callbacks=callbacks)
        # Return a `Markup` element considered as safe by Jinja.
        return Markup(html)


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
    rendered = md(value)
    text = do_striptags(rendered)
    if length > 0:
        text = do_truncate(text, length, end=end)
    return text


def init_app(app):
    parser = CommonMark.Parser  # Not an instance because not thread-safe(?)
    renderer = CommonMark.HtmlRenderer()
    app.extensions['markdown'] = UDataMarkdown(app, parser, renderer)

    app.add_template_filter(mdstrip)
