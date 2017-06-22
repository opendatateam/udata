# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from udata.tests import TestCase


from udata.rdf import negociate_content, want_rdf, ACCEPTED_MIME_TYPES


class ContentNegociationTest(TestCase):
    def test_find_format_from_accept_header(self):
        for mime, expected in ACCEPTED_MIME_TYPES.items():
            headers = {'accept': mime}
            with self.app.test_request_context(headers=headers):
                self.assertEqual(negociate_content(), expected)

    def test_default_format_if_no_accept_header(self):
        with self.app.test_request_context():
            self.assertEqual(negociate_content(default='json-ld'), 'json-ld')

    def test_default_format_if_unkown_accept_header(self):
        headers = {'accept': 'what/ever'}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(default='json-ld'), 'json-ld')

    def test_support_accept_header_multiple_form(self):
        headers = {'accept': 'application/xml, application/json'}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), 'xml')

    def test_support_accept_header_multiple_form_with_ponderation(self):
        headers = {'accept': 'application/xml;q=0.8, application/json;q=0.9'}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), 'json-ld')

    def test_match_known_format_in_accept_header(self):
        headers = {'accept': 'what/ever, application/xml'}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), 'xml')

    def test_want_rdf(self):
        for mimetype in 'application/xml', 'application/json':
            headers = {'accept': mimetype}
            with self.app.test_request_context(headers=headers):
                self.assertTrue(want_rdf())

    def test_want_html(self):
        for mimetype in 'text/html', 'application/xhtml+xml':
            headers = {'accept': mimetype}
            with self.app.test_request_context(headers=headers):
                self.assertFalse(want_rdf())

        with self.app.test_request_context():
            self.assertFalse(want_rdf())
