from functools import partial
from urllib.parse import urlparse

import bleach
import html2text
import mistune
import re

from bleach.linkifier import LinkifyFilter
from flask import current_app, Markup, request
from werkzeug.local import LocalProxy
from jinja2.filters import do_truncate, do_striptags

from udata.i18n import _


md = LocalProxy(lambda: current_app.extensions['markdown'])

EXCERPT_TOKEN = '<!--- --- -->'

RE_AUTOLINK = re.compile(
    r'<([A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\x00-\x20]*)>',
    re.IGNORECASE)


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

    if (None, 'href') not in attrs:
        return attrs
    parsed_url = urlparse(attrs[(None, 'href')])
    if parsed_url.netloc in ('', current_app.config['SERVER_NAME']):
        path = parsed_url.path
        attrs[(None, 'href')] = '{scheme}://{netloc}{path}{query}'.format(
            scheme='https' if request.is_secure else 'http',
            netloc=current_app.config['SERVER_NAME'],
            path=path if path.startswith('/') else f'/{path}',
            query='?' + parsed_url.query if parsed_url.query else '')
        return attrs
    else:
        rel = [x for x in attrs.get((None, 'rel'), '').split(' ') if x]
        if 'nofollow' not in [x.lower() for x in rel]:
            rel.append('nofollow')
        attrs[(None, 'rel')] = ' '.join(rel)
        return attrs


class Renderer(mistune.Renderer):
    def table(self, header, body):
        return (
            '<table>\n<thead>\n%s</thead>\n'
            '<tbody>\n%s</tbody>\n</table>\n'
        ) % (header, body)


class UdataCleaner(bleach.Cleaner):
    def __init__(self, source_tooltip=False) -> None:
        callbacks = [nofollow_callback]
        if source_tooltip:
            callbacks.append(source_tooltip_callback)

        super().__init__(
            tags=current_app.config['MD_ALLOWED_TAGS'],
            attributes=current_app.config['MD_ALLOWED_ATTRIBUTES'],
            styles=current_app.config['MD_ALLOWED_STYLES'],
            protocols=current_app.config['MD_ALLOWED_PROTOCOLS'],
            strip_comments=False,
            filters=[partial(LinkifyFilter, skip_tags=['pre'], parse_email=False,
                             callbacks=callbacks)])


class UDataMarkdown(object):
    """Consistent with Flask's extensions signature."""

    def __init__(self, app):
        app.jinja_env.filters.setdefault('markdown', self.__call__)
        renderer = Renderer(escape=False, hard_wrap=True)
        self.markdown = mistune.Markdown(renderer=renderer)

    def __call__(self, stream, source_tooltip=False, wrap=True):
        if not stream:
            return ''

        # Prepare angle bracket autolinks to avoid bleach treating them as tag
        stream = RE_AUTOLINK.sub(r'[\g<1>](\g<1>)', stream)
        # Turn markdown to HTML.
        html = self.markdown(stream)

        cleaner = UdataCleaner(source_tooltip)
        html = cleaner.clean(html)

        if wrap:
            html = '<div class="markdown">{0}</div>'.format(html.strip())
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
    rendered = md(value, wrap=False)
    text = do_striptags(rendered)
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
    app.extensions['markdown'] = UDataMarkdown(app)
    app.add_template_filter(mdstrip)
