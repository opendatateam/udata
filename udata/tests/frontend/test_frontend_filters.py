# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, render_template_string

from . import FrontTestCase

from udata.frontend.helpers import in_url


class FrontEndRootTest(FrontTestCase):
    def test_rewrite(self):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('front.home', one='value', two='two')
        expected = self.full_url('front.home', one='other-value', two=2)

        with self.app.test_request_context(url):
            result = render_template_string("{{ url_rewrite(one='other-value', two=2) }}")

        self.assertEqual(result, expected)

    def test_rewrite_append(self):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('front.home')
        expected = self.full_url('front.home', one='value')

        with self.app.test_request_context(url):
            result = render_template_string("{{ url_rewrite(one='value') }}")

        self.assertEqual(result, expected)

    def test_url_add(self):
        '''url_add should add a parameter to the URL'''
        url = url_for('front.home', one='value')

        result = render_template_string("{{ url|url_add(two='other') }}", url=url)

        self.assertEqual(result, url_for('front.home', one='value', two='other'))

    def test_url_add_append(self):
        '''url_add should add a parameter to the URL even if exists'''
        url = url_for('front.home', one='value')
        expected = url_for('front.home', one=['value', 'other-value'])

        result = render_template_string("{{ url|url_add(one='other-value') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_name(self):
        '''url_del should delete a parameter by name from the URL'''
        url = url_for('front.home', one='value', two='other')
        expected = url_for('front.home', two='other')

        result = render_template_string("{{ url|url_del('one') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_value(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('front.home', one=['value', 'other-value'], two='other')
        expected = url_for('front.home', one='value', two='other')

        result = render_template_string("{{ url|url_del(one='other-value') }}", url=url)

        self.assertEqual(result, expected)

    def test_url_del_by_value_not_string(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('front.home', one=['value', 42], two='other')
        expected = url_for('front.home', one='value', two='other')

        result = render_template_string("{{ url|url_del(one=42) }}", url=url)

        self.assertEqual(result, expected)

    def test_args_in_url(self):
        '''in_url() should test the presence of a key in url'''
        url = url_for('front.home', key='value', other='other')

        with self.app.test_request_context(url):
            self.assertTrue(in_url('key'))
            self.assertTrue(in_url('other'))
            self.assertTrue(in_url('key', 'other'))
            self.assertFalse(in_url('fake'))
            self.assertFalse(in_url('key', 'fake'))

    def test_kwargs_in_url(self):
        '''in_url() should test the presence of key/value pair in url'''
        url = url_for('front.home', key='value', other='other')

        with self.app.test_request_context(url):
            self.assertTrue(in_url(key='value'))
            self.assertTrue(in_url(key='value', other='other'))
            self.assertFalse(in_url(key='other'))
            self.assertFalse(in_url(key='value', other='value'))

            self.assertTrue(in_url('other', key='value'))

    def test_as_filter(self):
        '''URL helpers should exists as filter'''
        url = url_for('front.home', one='value')

        self.assertEqual(
            render_template_string("{{ url|url_rewrite(one='other-value') }}", url=url),
            url_for('front.home', one='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url|url_add(two='other-value') }}", url=url),
            url_for('front.home', one='value', two='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url|url_del('one') }}", url=url),
            url_for('front.home')
        )

    def test_as_global(self):
        '''URL helpers should exists as global function'''
        url = url_for('front.home', one='value')

        self.assertEqual(
            render_template_string("{{ url_rewrite(url, one='other-value') }}", url=url),
            url_for('front.home', one='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url_add(url, two='other-value') }}", url=url),
            url_for('front.home', one='value', two='other-value')
        )
        self.assertEqual(
            render_template_string("{{ url_del(url, 'one') }}", url=url),
            url_for('front.home')
        )

    def test_as_global_default(self):
        '''URL helpers should exists as global function without url parameter'''
        url = url_for('front.home', one='value')

        with self.app.test_request_context(url):
            self.assertEqual(
                render_template_string("{{ url_rewrite(one='other-value') }}"),
                self.full_url('front.home', one='other-value')
            )
            self.assertEqual(
                render_template_string("{{ url_add(two='other-value') }}"),
                self.full_url('front.home', one='value', two='other-value')
            )
            self.assertEqual(
                render_template_string("{{ url_del(None, 'one') }}"),
                self.full_url('front.home')
            )
            self.assertEqual(
                render_template_string("{{ in_url('one') }}"),
                'True'
            )
            self.assertEqual(
                render_template_string("{{ in_url('one') }}"),
                'True'
            )
            self.assertEqual(
                render_template_string("{{ in_url('two') }}"),
                'False'
            )
