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

    def test_excerpt_is_not_removed(self):
        with self.app.test_request_context('/'):
            self.assertEqual(md(EXCERPT_TOKEN).strip(), EXCERPT_TOKEN)

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

    def test_markdown_linkify_mails(self):
        '''Markdown filter should transform emails to anchors'''
        text = 'coucou@cmoi.fr'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('href'), 'mailto:coucou@cmoi.fr')
            self.assertEqual(el.firstChild.data, 'coucou@cmoi.fr')

    def test_markdown_linkify_within_pre(self):
        '''Markdown filter should not transform urls into <pre> anchors'''
        text = '<pre>http://example.net/</pre>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            self.assertEqual(result.strip(), '<pre>http://example.net/</pre>')

    def test_markdown_linkify_email_within_pre(self):
        '''Markdown filter should not transform emails into <pre> anchors'''
        text = '<pre>coucou@cmoi.fr</pre>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            self.assertEqual(result.strip(), '<pre>coucou@cmoi.fr</pre>')

    def test_bleach_sanitize(self):
        '''Markdown filter should sanitize evil code'''
        text = 'an <script>evil()</script>'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            self.assertEqual(result.strip(),
                             '<p>an &lt;script&gt;evil()&lt;/script&gt;</p>')

    def test_mdstrip_filter(self):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(7) }}', text=text)

        self.assertEqual(result, '1 2 ...')

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
