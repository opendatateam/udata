# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import html5lib

from flask import render_template_string

from .. import TestCase, WebTestMixin

from udata.frontend.markdown import md, init_app, EXCERPT_TOKEN

parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))


class MarkdownTestCase(TestCase, WebTestMixin):
    def create_app(self):
        app = super(MarkdownTestCase, self).create_app()
        init_app(app)
        return app

    def assert_md_equal(self, value, expected):
        expected = '<div class="markdown">{0}</div>'.format(expected)
        self.assertEqual(value.strip(), expected)

    def test_excerpt_is_not_removed(self):
        with self.app.test_request_context('/'):
            self.assert_md_equal(md(EXCERPT_TOKEN), EXCERPT_TOKEN)

    def test_markdown_filter_with_none(self):
        '''Markdown filter should not fails with None'''
        text = None
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)

        self.assertEqual(result, '')

    def test_markdown_links_nofollow(self):
        '''Markdown filter should render links as nofollow'''
        text = '[example](http://example.net/ "Title")'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), 'nofollow')
            self.assertEqual(el.getAttribute('href'), 'http://example.net/')
            self.assertEqual(el.getAttribute('title'), 'Title')
            self.assertEqual(el.firstChild.data, 'example')

    def test_markdown_linkify(self):
        '''Markdown filter should transform urls to anchors'''
        text = 'http://example.net/'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), 'nofollow')
            self.assertEqual(el.getAttribute('href'), 'http://example.net/')
            self.assertEqual(el.firstChild.data, 'http://example.net/')

    def test_markdown_linkify_relative(self):
        '''Markdown filter should transform relative urls to external ones'''
        text = '[foo](/)'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), '')
            self.assertEqual(el.getAttribute('href'), 'http://localhost/')
            self.assertEqual(el.getAttribute('data-tooltip'), '')
            self.assertEqual(el.firstChild.data, 'foo')

    def test_markdown_linkify_https(self):
        '''Markdown filter should transform relative urls with HTTPS'''
        text = '[foo](/foo)'
        with self.app.test_request_context('/', base_url='https://localhost'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), '')
            self.assertEqual(el.getAttribute('href'), 'https://localhost/foo')
            self.assertEqual(el.getAttribute('data-tooltip'), '')
            self.assertEqual(el.firstChild.data, 'foo')

    def test_markdown_linkify_relative_with_tooltip(self):
        '''Markdown filter should transform + add tooltip'''
        text = '[foo](/)'
        with self.app.test_request_context('/'):
            result = render_template_string(
                '{{ text|markdown(source_tooltip=True) }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), '')
            self.assertEqual(el.getAttribute('href'), 'http://localhost/')
            self.assertEqual(el.getAttribute('data-tooltip'), 'Source')
            self.assertEqual(el.firstChild.data, 'foo')

    def test_markdown_not_linkify_mails(self):
        '''Markdown filter should not transform emails to anchors'''
        text = 'coucou@cmoi.fr'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            self.assertEqual(parsed.getElementsByTagName('a'), [])
            self.assert_md_equal(result, '<p>coucou@cmoi.fr</p>')

    def test_markdown_linkify_within_pre(self):
        '''Markdown filter should not transform urls into <pre> anchors'''
        text = '<pre>http://example.net/</pre>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            self.assert_md_equal(result, '<pre>http://example.net/</pre>')

    def test_markdown_linkify_email_within_pre(self):
        '''Markdown filter should not transform emails into <pre> anchors'''
        text = '<pre>coucou@cmoi.fr</pre>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            self.assert_md_equal(result, '<pre>coucou@cmoi.fr</pre>')

    def test_bleach_sanitize(self):
        '''Markdown filter should sanitize evil code'''
        text = 'an <script>evil()</script>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            expected = '<p>an &lt;script&gt;evil()&lt;/script&gt;</p>'
            self.assert_md_equal(result, expected)

    def test_soft_break(self):
        '''Markdown should treat soft breaks as br tag'''
        text = 'line 1\nline 2'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            expected = '<p>line 1<br>line 2</p>'
            self.assert_md_equal(result, expected)

    def test_mdstrip_filter(self):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(7) }}', text=text)

        self.assertEqual(result, '1 2 3…')

    def test_mdstrip_filter_does_not_truncate_without_size(self):
        '''mdstrip should not truncate by default'''
        text = 'aaaa ' * 300
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        self.assertEqual(result.strip(), text.strip())

    def test_mdstrip_filter_with_none(self):
        '''mdstrip filter should not fails with None'''
        text = None
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        self.assertEqual(result, '')

    def test_mdstrip_filter_with_excerpt(self):
        '''mdstrip should truncate on token if shorter than required size'''
        text = ''.join(['excerpt', EXCERPT_TOKEN, 'aaaa ' * 10])
        with self.app.test_request_context('/'):
            result = render_template_string(
                '{{ text|mdstrip(20) }}', text=text)

        self.assertEqual(result, 'excerpt')

    def test_mdstrip_does_not_truncate_in_tags(self):
        '''mdstrip should not truncate in middle of a tag'''
        text = '![Legend](http://www.somewhere.com/image.jpg) Here. aaaaa'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(5) }}', text=text)

        self.assertEqual(result.strip(), 'Here…')

    def test_mdstrip_custom_end(self):
        '''mdstrip should allow a custom ending string'''
        text = '1234567890'
        template = '{{ text|mdstrip(5, "$") }}'
        with self.app.test_request_context('/'):
            result = render_template_string(template, text=text)

        self.assertEqual(result.strip(), '1234$')
