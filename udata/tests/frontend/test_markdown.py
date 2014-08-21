# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import render_template_string

from .. import TestCase, WebTestMixin

from udata.frontend.markdown import md, init_app, EXCERPT_TOKEN


class MarkdownTestCase(TestCase, WebTestMixin):
    def create_app(self):
        app = super(MarkdownTestCase, self).create_app()
        init_app(app)
        return app

    def test_excerpt_is_not_removed(self):
        with self.app.test_request_context('/'):
            self.assertEqual(md('<!--- excerpt -->'), '<!--- excerpt -->')

    def test_markdown_filter_with_none(self):
        '''Markdown filter should not fails with None'''
        text = None
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)

        self.assertEqual(result, '')

    def test_mdstrip_filter(self):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(5) }}', text=text)

        self.assertEqual(result, '1 2 ...')

    def test_mdstrip_filter_does_not_truncate_wuthout_size(self):
        '''mdstrip should truncate to 128 characters by default'''
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
        '''mdstrip should truncate to 128 characters by default'''
        text = ''.join(['excerpt', EXCERPT_TOKEN, 'aaaa ' * 10])
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(20) }}', text=text)

        self.assertEqual(result, 'excerpt')
