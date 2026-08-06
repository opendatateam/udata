import pytest
from rdflib import (
    BNode,
    Graph,
    Literal,
    URIRef,
)
from rdflib.resource import Resource as RdfResource

from udata.core.organization.factories import OrganizationFactory
from udata.models import ContactPoint
from udata.rdf import (
    ACCEPTED_MIME_TYPES,
    AGENT_ROLE_TO_RDF_PREDICATE,
    CONTACT_POINT_ENTITY_TO_ROLE,
    DCAT,
    DCT,
    FOAF,
    FORMAT_MAP,
    ORG,
    RDF,
    SKOS,
    VCARD,
    contact_point_from_foaf,
    contact_point_from_vcard,
    contact_points_from_rdf,
    contact_points_to_rdf,
    guess_format,
    negociate_content,
    vocabulary_key,
    want_rdf,
)
from udata.tests import TestCase
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import argvalues


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
            assert contact_point.value(VCARD.hasURL).identifier == URIRef(
                "https://data.support.com"
            )
            # Default predicate is "contact"
            assert predicate == DCAT.contactPoint

    @pytest.mark.parametrize("role,predicate", AGENT_ROLE_TO_RDF_PREDICATE.items())
    def test_contact_points_to_rdf_roles(self, role, predicate):
        contact = ContactPoint(
            name="Organization contact",
            email="hello@its.me",
            contact_form="https://data.support.com",
            role=role,
        )

        contact_rdfs = contact_points_to_rdf([contact], None)

        for contact_point, contact_point_predicate in contact_rdfs:
            assert contact_point_predicate == predicate
            if predicate == DCAT.contactPoint:
                assert contact_point.value(RDF.type).identifier == VCARD.Kind
                assert contact_point.value(VCARD.fn) == Literal("Organization contact")
                assert contact_point.value(VCARD.hasEmail).identifier == URIRef(
                    "mailto:hello@its.me"
                )
                assert contact_point.value(VCARD.hasURL).identifier == URIRef(
                    "https://data.support.com"
                )
            else:
                assert contact_point.value(RDF.type).identifier == FOAF.Agent
                assert contact_point.value(FOAF.name) == Literal("Organization contact")
                assert contact_point.value(FOAF.mbox).identifier == URIRef("mailto:hello@its.me")
                assert contact_point.value(FOAF.page).identifier == URIRef(
                    "https://data.support.com"
                )


class ContactFromRdfTest(PytestOnlyDBTestCase):
    cases = [  # (user_info, org_info, id)
        (
            ("me", "me@example.com", "http://example.com/me"),
            None,
            "individual-full",
        ),
        (
            None,
            ("org", "org@example.com", "http://example.com/org"),
            "organization-full",
        ),
        (
            ("me", "me@example.com", "http://example.com/me"),
            ("org", "org@example.com", "http://example.com/org"),
            "both-full",
        ),
        (
            (None, "me@example.com", "http://example.com/me"),
            None,
            "individual-noname",
        ),
        (
            ("me", None, "http://example.com/me"),
            None,
            "individual-noemail",
        ),
        (
            ("me", "me@example.com", None),
            None,
            "individual-noform",
        ),
        (
            (None, None, None),
            None,
            "individual-nothing",
        ),
        (
            None,
            (None, "org@example.com", "http://example.com/org"),
            "organization-noname",
        ),
        (
            None,
            ("org", None, "http://example.com/org"),
            "organization-noemail",
        ),
        (
            None,
            ("org", "org@example.com", None),
            "organization-noform",
        ),
        (
            None,
            (None, None, None),
            "organization-nothing",
        ),
        (
            ("me", "me@example.com", "http://example.com/me"),
            (None, "org@example.com", "http://example.com/org"),
            "both-noorgname",
        ),
        (
            ("me", "me@example.com", "http://example.com/me"),
            ("org", None, "http://example.com/org"),
            "both-noorgemail",
        ),
        # (
        #     "both-noorgform" => currently not supported in either VCARD or FOAF
        # ),
        (
            (None, "me@example.com", "http://example.com/me"),
            ("org", "org@example.com", "http://example.com/org"),
            "both-nousername",
        ),
        (
            ("me", None, "http://example.com/me"),
            ("org", "org@example.com", "http://example.com/org"),
            "both-nouseremail",
        ),
        (
            (None, "me@example.com", "http://example.com/me"),
            (None, "org@example.com", "http://example.com/org"),
            "both-noname",
        ),
        (
            ("me", None, "http://example.com/me"),
            ("org", None, "http://example.com/org"),
            "both-noemail",
        ),
    ]

    @pytest.mark.parametrize("user_info, org_info", argvalues(cases))
    @pytest.mark.parametrize("typed", [True, False], ids=["typed", "untyped"])
    @pytest.mark.parametrize(
        "predicate", [DCAT.contactPoint, DCT.creator], ids=["compliant", "lenient"]
    )
    def test_contact_points_from_rdf_vcard(self, user_info, org_info, typed, predicate):
        user_name, user_email, user_form = user_info or (None, None, None)
        org_name, org_email, org_form = org_info or (None, None, None)
        role = CONTACT_POINT_ENTITY_TO_ROLE[predicate]

        expected_name, expected_email, expected_form = ("", None, None)
        g = Graph()
        root = BNode()
        contact = BNode()
        if user_info:
            if typed:
                g.add((contact, RDF.type, VCARD.Individual))
            if user_name:
                g.add((contact, VCARD.fn, Literal(user_name)))
                expected_name = user_name
            if user_email:
                g.add((contact, VCARD.hasEmail, Literal("mailto:" + user_email)))
                expected_email = user_email
            if user_form:
                g.add((contact, VCARD.hasURL, Literal(user_form)))
                expected_form = user_form
            # Only the org name can appear on an individual VCARD
            if org_name:
                g.add((contact, VCARD["organization-name"], Literal(org_name)))
                expected_name = f"{user_name} ({org_name})" if user_name else org_name
        elif org_info:
            if typed:
                g.add((contact, RDF.type, VCARD.Organization))
            if org_name:
                g.add((contact, VCARD.fn, Literal(org_name)))
                expected_name = org_name
            if org_email:
                g.add((contact, VCARD.email, Literal("mailto:" + org_email)))
                expected_email = org_email
            if org_form:
                g.add((contact, VCARD.hasURL, Literal(org_form)))
                expected_form = org_form
        g.add((root, predicate, contact))

        contact_points = list(
            contact_points_from_rdf(
                RdfResource(g, root), predicate, role, OrganizationFactory(name="foo")
            )
        )

        if not any([expected_name, expected_email, expected_form]):
            # Empty contact
            assert len(contact_points) == 0
        elif role == "contact" and not (expected_email or expected_form):
            # ContactPoint.validate() rule
            assert len(contact_points) == 0
        else:
            assert len(contact_points) == 1
            assert contact_points[0].role == role
            assert contact_points[0].name == expected_name
            assert contact_points[0].email == expected_email
            assert contact_points[0].contact_form == expected_form

    @pytest.mark.parametrize("user_info, org_info", argvalues(cases))
    @pytest.mark.parametrize("typed", [True, False], ids=["typed", "untyped"])
    @pytest.mark.parametrize(
        "predicate", [DCT.creator, DCAT.contactPoint], ids=["compliant", "lenient"]
    )
    def test_contact_points_from_rdf_foaf(self, user_info, org_info, typed, predicate):
        # No support for contact_form in FOAF
        user_name, user_email, _ = user_info or (None, None, None)
        org_name, org_email, _ = org_info or (None, None, None)
        role = CONTACT_POINT_ENTITY_TO_ROLE[predicate]

        expected_name, expected_email = ("", None)
        g = Graph()
        root = BNode()
        contact = BNode()
        if user_info:
            if typed:
                g.add((contact, RDF.type, FOAF.Person))
            if user_name:
                g.add((contact, FOAF.name, Literal(user_name)))
                expected_name = user_name
            if user_email:
                g.add((contact, FOAF.mbox, Literal("mailto:" + user_email)))
                expected_email = user_email
            if org_name or org_email:
                org = BNode()
                if typed:
                    g.add((org, RDF.type, FOAF.Organization))
                if org_name:
                    g.add((org, FOAF.name, Literal(org_name)))
                    expected_name = f"{user_name} ({org_name})" if user_name else org_name
                if org_email:
                    g.add((org, FOAF.mbox, Literal(org_email)))
                    expected_email = user_email if user_email else org_email
                g.add((contact, ORG.memberOf, org))
        elif org_info:
            if typed:
                g.add((contact, RDF.type, FOAF.Organization))
            if org_name:
                g.add((contact, FOAF.name, Literal(org_name)))
                expected_name = org_name
            if org_email:
                g.add((contact, FOAF.mbox, Literal("mailto:" + org_email)))
                expected_email = org_email
        g.add((root, predicate, contact))

        contact_points = list(
            contact_points_from_rdf(
                RdfResource(g, root), predicate, role, OrganizationFactory(name="foo")
            )
        )

        if not any([expected_name, expected_email]):
            # Empty contact
            assert len(contact_points) == 0
        elif role == "contact" and not expected_email:
            # ContactPoint.validate() rule
            assert len(contact_points) == 0
        else:
            assert len(contact_points) == 1
            assert contact_points[0].role == role
            assert contact_points[0].name == expected_name
            assert contact_points[0].email == expected_email
            assert contact_points[0].contact_form is None

    @pytest.mark.parametrize(
        "predicate", [DCAT.contactPoint, DCT.creator], ids=["contact", "creator"]
    )
    def test_contact_points_from_rdf_literal(self, predicate):
        role = CONTACT_POINT_ENTITY_TO_ROLE[predicate]

        expected_name = "foo"
        g = Graph()
        root = BNode()
        g.add((root, predicate, Literal(expected_name)))

        contact_points = list(
            contact_points_from_rdf(
                RdfResource(g, root), predicate, role, OrganizationFactory(name="foo")
            )
        )

        if role == "contact":
            # ContactPoint.validate() rule
            assert len(contact_points) == 0
        else:
            assert len(contact_points) == 1
            assert contact_points[0].role == role
            assert contact_points[0].name == expected_name
            assert contact_points[0].email is None
            assert contact_points[0].contact_form is None

    @pytest.mark.parametrize(
        "property",
        [VCARD.fn, VCARD["organization-name"]],
        ids=lambda u: vocabulary_key(u, VCARD),
    )
    def test_contact_point_from_vcard_name(self, property):
        expected_name = "foo"
        g = Graph()
        contact = BNode()
        g.add((contact, property, Literal(expected_name)))

        name, _, _ = contact_point_from_vcard(RdfResource(g, contact))

        assert name == expected_name

    @pytest.mark.parametrize(
        "property",
        [VCARD["organization-name"], VCARD["organisation-name"]],
        ids=lambda u: vocabulary_key(u, VCARD),
    )
    def test_contact_point_from_vcard_name_deprecated(self, property):
        expected_name = "foo"
        g = Graph()
        org = BNode()
        g.add((org, property, Literal(expected_name)))
        contact = BNode()
        g.add((contact, RDF.type, VCARD.Organization))
        g.add((contact, VCARD.org, org))  # deprecated vcard:org spec

        name, _, _ = contact_point_from_vcard(RdfResource(g, contact))

        assert name == expected_name

    def test_contact_point_from_vcard_org_missing(self):
        expected_name = "foo"
        g = Graph()
        org = BNode()  # anonymous org node with no relevant org info
        contact = BNode()
        g.add((contact, RDF.type, VCARD.Organization))
        g.add((contact, VCARD.fn, Literal(expected_name)))
        g.add((contact, VCARD.org, org))  # deprecated vcard:org spec

        name, _, _ = contact_point_from_vcard(RdfResource(g, contact))

        assert name == expected_name

    @pytest.mark.parametrize("namespaced", [True, False], ids=["namespaced", "plain"])
    @pytest.mark.parametrize(
        "property",
        [VCARD.hasEmail, VCARD.email],
        ids=lambda u: vocabulary_key(u, VCARD),
    )
    def test_contact_point_from_vcard_email(self, namespaced, property):
        expected_email = "foo@example.com"
        g = Graph()
        contact = BNode()
        g.add((contact, property, Literal(("mailto:" if namespaced else "") + expected_email)))

        _, email, _ = contact_point_from_vcard(RdfResource(g, contact))

        assert email == expected_email

    @pytest.mark.parametrize(
        "property",
        [VCARD.hasURL, VCARD.url, VCARD.hasUrl],
        ids=lambda u: vocabulary_key(u, VCARD),
    )
    def test_contact_point_from_vcard_url(self, property):
        expected_form = "http://example.com/foo"
        g = Graph()
        contact = BNode()
        g.add((contact, property, Literal(expected_form)))

        _, _, form = contact_point_from_vcard(RdfResource(g, contact))

        assert form == expected_form

    @pytest.mark.parametrize(
        "property",
        [FOAF.name, SKOS.prefLabel],
        ids=["foaf:name", "skos:prefLabel"],
    )
    def test_contact_point_from_foaf_name(self, property):
        expected_name = "foo"
        g = Graph()
        contact = BNode()
        g.add((contact, property, Literal(expected_name)))

        name, _, _ = contact_point_from_foaf(RdfResource(g, contact))

        assert name == expected_name

    def test_contact_point_from_foaf_name_memberOf(self):
        expected_name = "foo"
        g = Graph()
        org = BNode()
        g.add((org, FOAF.name, Literal(expected_name)))
        contact = BNode()
        g.add((contact, ORG.memberOf, org))

        name, _, _ = contact_point_from_foaf(RdfResource(g, contact))

        assert name == expected_name

    @pytest.mark.parametrize("namespaced", [True, False], ids=["namespaced", "plain"])
    def test_contact_point_from_foaf_email(self, namespaced):
        expected_email = "foo@example.com"
        g = Graph()
        contact = BNode()
        g.add((contact, FOAF.mbox, Literal(("mailto:" if namespaced else "") + expected_email)))

        _, email, _ = contact_point_from_foaf(RdfResource(g, contact))

        assert email == expected_email

    @pytest.mark.parametrize("namespaced", [True, False], ids=["namespaced", "plain"])
    def test_contact_point_from_foaf_email_memberOf(self, namespaced):
        expected_email = "foo@example.com"
        g = Graph()
        org = BNode()
        g.add((org, FOAF.mbox, Literal(("mailto:" if namespaced else "") + expected_email)))
        contact = BNode()
        g.add((contact, ORG.memberOf, org))

        _, email, _ = contact_point_from_foaf(RdfResource(g, contact))

        assert email == expected_email

    def test_contact_point_from_foaf_org_missing(self):
        expected_name = "foo"
        g = Graph()
        org = BNode()  # anonymous org node with no relevant org info
        contact = BNode()
        g.add((contact, FOAF.name, Literal(expected_name)))
        g.add((contact, ORG.memberOf, org))

        name, _, _ = contact_point_from_foaf(RdfResource(g, contact))

        assert name == expected_name
