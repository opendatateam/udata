import pytest
from rdflib import (
    Literal,
    URIRef,
)

from udata.models import ContactPoint
from udata.rdf import (
    ACCEPTED_MIME_TYPES,
    DCAT,
    DCT,
    FORMAT_MAP,
    RDF,
    VCARD,
    contact_points_to_rdf,
    guess_format,
    negociate_content,
    want_rdf,
)
from udata.tests import TestCase


class ContentNegociationTest(TestCase):
    def test_find_format_from_accept_header(self):
        for mime, expected in ACCEPTED_MIME_TYPES.items():
            headers = {"accept": mime}
            with self.app.test_request_context(headers=headers):
                self.assertEqual(negociate_content(), expected)

    def test_default_format_if_no_accept_header(self):
        with self.app.test_request_context():
            self.assertEqual(negociate_content(default="json-ld"), "json-ld")

    def test_default_format_if_unkown_accept_header(self):
        headers = {"accept": "what/ever"}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(default="json-ld"), "json-ld")

    def test_support_accept_header_multiple_form(self):
        headers = {"accept": "application/xml, application/json"}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), "xml")

    def test_support_accept_header_multiple_form_with_ponderation(self):
        headers = {"accept": "application/xml;q=0.8, application/json;q=0.9"}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), "json-ld")

    def test_match_known_format_in_accept_header(self):
        headers = {"accept": "what/ever, application/xml"}
        with self.app.test_request_context(headers=headers):
            self.assertEqual(negociate_content(), "xml")

    def test_want_rdf(self):
        for mimetype in "application/xml", "application/json":
            headers = {"accept": mimetype}
            with self.app.test_request_context(headers=headers):
                self.assertTrue(want_rdf())

    def test_want_html(self):
        for mimetype in "text/html", "application/xhtml+xml":
            headers = {"accept": mimetype}
            with self.app.test_request_context(headers=headers):
                self.assertFalse(want_rdf())

        with self.app.test_request_context():
            self.assertFalse(want_rdf())


class GuessFormatTest(object):
    @pytest.mark.parametrize("suffix,expected", FORMAT_MAP.items())
    def test_guess_from_extension(self, suffix, expected):
        assert guess_format("resource.{0}".format(suffix)) == expected

    @pytest.mark.parametrize("mime,expected", ACCEPTED_MIME_TYPES.items())
    def test_guess_from_mime_type(self, mime, expected):
        assert guess_format(mime) == expected

    def test_unkown_extension(self):
        assert guess_format("resource.unknonn") is None

    def test_unkown_mime(self):
        assert guess_format("unknown/mime") is None


class ContactToRdfTest:
    def test_contact_points_to_rdf(self):
        contact = ContactPoint(
            name="Organization contact",
            email="hello@its.me",
            contact_form="https://data.support.com",
        )

        contact_rdfs = contact_points_to_rdf([contact], None)

        for contact_point, predicate in contact_rdfs:
            assert contact_point.value(RDF.type).identifier == VCARD.Kind
            assert contact_point.value(VCARD.fn) == Literal("Organization contact")
            assert contact_point.value(VCARD.hasEmail).identifier == URIRef("mailto:hello@its.me")
            assert contact_point.value(VCARD.hasUrl).identifier == URIRef(
                "https://data.support.com"
            )
            # Default predicate is "contact"
            assert predicate == DCAT.contactPoint

    @pytest.mark.parametrize(
        "role,predicate",
        [
            ("contact", DCAT.contactPoint),
            ("publisher", DCT.publisher),
            ("creator", DCT.creator),
        ],
    )
    def test_contact_points_to_rdf_roles(self, role, predicate):
        contact = ContactPoint(
            name="Organization contact",
            email="hello@its.me",
            contact_form="https://data.support.com",
            role=role,
        )

        contact_rdfs = contact_points_to_rdf([contact], None)

        for contact_point, contact_point_predicate in contact_rdfs:
            assert contact_point.value(RDF.type).identifier == VCARD.Kind
            assert contact_point.value(VCARD.fn) == Literal("Organization contact")
            assert contact_point.value(VCARD.hasEmail).identifier == URIRef("mailto:hello@its.me")
            assert contact_point.value(VCARD.hasUrl).identifier == URIRef(
                "https://data.support.com"
            )
            assert contact_point_predicate == predicate
