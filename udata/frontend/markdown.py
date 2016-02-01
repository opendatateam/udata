# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import bleach
import CommonMark
from html5lib.sanitizer import HTMLSanitizer
from flask import current_app, Markup
from werkzeug.local import LocalProxy
from jinja2.filters import do_truncate, do_striptags

md = LocalProxy(lambda: current_app.extensions['markdown'])

EXCERPT_TOKEN = '<!--- --- -->'


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

    def __call__(self, stream):
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
        # Turn string links into HTML ones *after* markdown transformation.
        html = bleach.linkify(html, tokenizer=KeepTokenSanitizer,
                              skip_pre=True, parse_email=True)
        # Return a `Markup` element considered as safe by Jinja.
        return Markup(html)


def init_app(app):
    parser = CommonMark.DocParser  # Not an instance because not thread-safe(?)
    renderer = CommonMark.HTMLRenderer()
    app.extensions['markdown'] = UDataMarkdown(app, parser, renderer)

    @app.template_filter()
    def mdstrip(value, length=None):
        '''
        Truncate and strip tags from a markdown source

        The markdown source is truncated at the excerpt if present and
        smaller than the required length. Then, all html tags are stripped.
        '''
        if not value:
            return ''
        if EXCERPT_TOKEN in value:
            value = value.split(EXCERPT_TOKEN, 1)[0]
        if length > 0:
            value = do_truncate(value, length, end='…')
        rendered = md(value)
        return do_striptags(rendered)
