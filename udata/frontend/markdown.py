# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.markdown import Markdown
from mdx_linkify.mdx_linkify import LinkifyExtension

from flask import current_app
from werkzeug.local import LocalProxy
from jinja2.filters import do_truncate, do_striptags


md = LocalProxy(lambda: current_app.extensions['markdown'])

EXCERPT_TOKEN = '<!--- --- -->'


class UDataMarkdown(Markdown):
    def __call__(self, stream):
        return super(UDataMarkdown, self).__call__(stream or '')


def set_nofollow(attrs, new=False):
    '''Ensure that Markdown links are 'rel="nofollow"' '''
    attrs['rel'] = 'nofollow'
    return attrs


def init_app(app):
    linkify = LinkifyExtension(configs={'linkify_callbacks': [set_nofollow]})
    app.extensions['markdown'] = UDataMarkdown(app, extensions=[linkify])

    @app.template_filter()
    def mdstrip(value, length=None):
        '''
        Truncate and strip tags from a markdown source

        The markdown source is truncated at the excerpt if present and smaller than the required length.
        Then, all html tags are stripped.
        '''
        if not value:
            return ''
        if EXCERPT_TOKEN in value:
            value = value.split(EXCERPT_TOKEN, 1)[0]
        if length > 0:
            value = do_truncate(value, length)
        rendered = md(value)
        return do_striptags(rendered)
