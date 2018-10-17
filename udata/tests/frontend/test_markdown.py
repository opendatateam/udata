# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from bleach._vendor import html5lib
from flask import render_template_string

from udata.frontend.markdown import md, parse_html, EXCERPT_TOKEN
from udata.utils import faker

parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))


def assert_md_equal(value, expected):
    __tracebackhide__ = True
    expected = '<div class="markdown">{0}</div>'.format(expected)
    assert value.strip() == expected


@pytest.mark.frontend
class MarkdownTest:
    def test_excerpt_is_not_removed(self, app):
        with app.test_request_context('/'):
            assert_md_equal(md(EXCERPT_TOKEN), EXCERPT_TOKEN)

    def test_markdown_filter_with_none(self, app):
        '''Markdown filter should not fails with None'''
        text = None
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)

        assert result == ''

    def test_markdown_links_nofollow(self, app):
        '''Markdown filter should render links as nofollow'''
        text = '[example](http://example.net/ "Title")'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == 'nofollow'
            assert el.getAttribute('href') == 'http://example.net/'
            assert el.getAttribute('title') == 'Title'
            assert el.firstChild.data == 'example'

    def test_markdown_linkify(self, app):
        '''Markdown filter should transform urls to anchors'''
        text = 'http://example.net/'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == 'nofollow'
            assert el.getAttribute('href') == 'http://example.net/'
            assert el.firstChild.data == 'http://example.net/'

    def test_markdown_linkify_angle_brackets(self, app):
        '''Markdown filter should transform urls to anchors'''
        text = '<http://example.net/path>'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == 'nofollow'
            assert el.getAttribute('href') == 'http://example.net/path'
            assert el.firstChild.data == 'http://example.net/path'

    def test_markdown_linkify_relative(self, app):
        '''Markdown filter should transform relative urls to external ones'''
        text = '[foo](/)'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == ''
            assert el.getAttribute('href') == 'http://local.test/'
            assert el.getAttribute('data-tooltip') == ''
            assert el.firstChild.data == 'foo'

    def test_markdown_linkify_https(self, app):
        '''Markdown filter should transform relative urls with HTTPS'''
        text = '[foo](/foo)'
        with app.test_request_context('/', base_url='https://local.test'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == ''
            assert el.getAttribute('href') == 'https://local.test/foo'
            assert el.getAttribute('data-tooltip') == ''
            assert el.firstChild.data == 'foo'

    def test_markdown_linkify_relative_with_tooltip(self, app):
        '''Markdown filter should transform + add tooltip'''
        text = '[foo](/)'
        with app.test_request_context('/'):
            result = render_template_string(
                '{{ text|markdown(source_tooltip=True) }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == ''
            assert el.getAttribute('href') == 'http://local.test/'
            assert el.getAttribute('data-tooltip') == 'Source'
            assert el.firstChild.data == 'foo'

    def test_markdown_not_linkify_mails(self, app):
        '''Markdown filter should not transform emails to anchors'''
        text = 'coucou@cmoi.fr'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            assert parsed.getElementsByTagName('a') == []
            assert_md_equal(result, '<p>coucou@cmoi.fr</p>')

    def test_markdown_linkify_within_pre(self, app):
        '''Markdown filter should not transform urls into <pre> anchors'''
        text = '<pre>http://example.net/</pre>'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            assert_md_equal(result, '<pre>http://example.net/</pre>')

    def test_markdown_linkify_email_within_pre(self, app):
        '''Markdown filter should not transform emails into <pre> anchors'''
        text = '<pre>coucou@cmoi.fr</pre>'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            assert_md_equal(result, '<pre>coucou@cmoi.fr</pre>')

    def test_bleach_sanitize(self, app):
        '''Markdown filter should sanitize evil code'''
        text = 'an <script>evil()</script>'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            expected = '<p>an &lt;script&gt;evil()&lt;/script&gt;</p>'
            assert_md_equal(result, expected)

    def test_soft_break(self, app):
        '''Markdown should treat soft breaks as br tag'''
        text = 'line 1\nline 2'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            expected = '<p>line 1<br>line 2</p>'
            assert_md_equal(result, expected)

    def test_mdstrip_filter(self, app):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(7) }}', text=text)

        assert result == '1 2 3…'

    def test_mdstrip_filter_does_not_truncate_without_size(self, app):
        '''mdstrip should not truncate by default'''
        text = 'aaaa ' * 300
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        assert result.strip() == text.strip()

    def test_mdstrip_filter_with_none(self, app):
        '''mdstrip filter should not fails with None'''
        text = None
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        assert result == ''

    def test_mdstrip_filter_with_excerpt(self, app):
        '''mdstrip should truncate on token if shorter than required size'''
        text = ''.join(['excerpt', EXCERPT_TOKEN, 'aaaa ' * 10])
        with app.test_request_context('/'):
            result = render_template_string(
                '{{ text|mdstrip(20) }}', text=text)

        assert result == 'excerpt'

    def test_mdstrip_does_not_truncate_in_tags(self, app):
        '''mdstrip should not truncate in middle of a tag'''
        text = '![Legend](http://www.somewhere.com/image.jpg) Here. aaaaa'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(5) }}', text=text)

        assert result.strip() == 'Here…'

    def test_mdstrip_custom_end(self, app):
        '''mdstrip should allow a custom ending string'''
        text = '1234567890'
        template = '{{ text|mdstrip(5, "$") }}'
        with app.test_request_context('/'):
            result = render_template_string(template, text=text)

        assert result.strip() == '1234$'


class HtmlToMarkdownTest:
    def test_string_is_untouched(self):
        assert parse_html('foo') == 'foo'

    def test_empty_string_is_untouched(self):
        assert parse_html('') == ''

    def test_none_is_empty_string(self):
        assert parse_html(None) == ''

    def test_parse_basic_html(self):
        text = faker.paragraph()
        html = '<div>{0}</div>'.format(text)

        assert parse_html(html) == text

    def test_content_is_stripped(self):
        text = faker.paragraph()
        spacer = '\n  ' * 3
        assert parse_html(spacer + text + spacer) == text

    def test_parse_html_anchors(self):
        html = '<a href="http://somewhere.com">title</a>'
        assert parse_html(html) == '[title](http://somewhere.com)'

    def test_parse_html_anchors_with_link_title(self):
        url = 'http://somewhere.com/some/path'
        html = '<a href="{0}">{0}</a>'.format(url)
        assert parse_html(html) == '<{0}>'.format(url)

    def test_parse_html_anchors_with_attribute(self):
        url = 'http://somewhere.com/some/path'
        html = '<a href="{0}" target="_blank" title="a title">title</a>'
        expected = '[title]({0} "a title")'

        assert parse_html(html.format(url)) == expected.format(url)
