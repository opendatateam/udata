from datetime import date
from xml.etree.ElementTree import XML

import pytest
import requests
from flask import url_for
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, RDF
from rdflib.resource import Resource as RdfResource

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.dataset.models import (
    Checksum,
    Dataset,
    HarvestDatasetMetadata,
    License,
    Resource,
)
from udata.core.dataset.rdf import (
    EU_RDF_REQUENCIES,
    dataset_from_rdf,
    dataset_to_rdf,
    frequency_from_rdf,
    frequency_to_rdf,
    licenses_from_rdf,
    resource_from_rdf,
    resource_to_rdf,
    temporal_from_rdf,
)
from udata.core.organization.factories import OrganizationFactory
from udata.i18n import gettext as _
from udata.mongo import db
from udata.rdf import (
    ADMS,
    DCAT,
    DCATAP,
    DCT,
    FREQ,
    HVD_LEGISLATION,
    SCHEMA,
    SKOS,
    SPDX,
    TAG_TO_EU_HVD_CATEGORIES,
    VCARD,
    primary_topic_identifier_from_rdf,
)
from udata.tests.helpers import assert200, assert_redirects
from udata.utils import faker

pytestmark = pytest.mark.usefixtures("app")

FREQ_SAMPLE = [
    (FREQ.annual, "annual"),
    (FREQ.monthly, "monthly"),
    (FREQ.daily, "daily"),
    (FREQ.continuous, "continuous"),
]

GOV_UK_REF = "http://reference.data.gov.uk/id/year/2017"

try:
    requests.head(GOV_UK_REF, timeout=0.1)
except requests.exceptions.RequestException:
    GOV_UK_REF_IS_UP = False
else:
    GOV_UK_REF_IS_UP = True


@pytest.mark.frontend
class DatasetToRdfTest:
    def test_minimal(self):
        dataset = DatasetFactory.build()  # Does not have an URL
        d = dataset_to_rdf(dataset)
        g = d.graph

        assert isinstance(d, RdfResource)
        assert len(list(g.subjects(RDF.type, DCAT.Dataset))) == 1

        assert g.value(d.identifier, RDF.type) == DCAT.Dataset

        assert isinstance(d.identifier, BNode)
        assert d.value(DCT.identifier) == Literal(dataset.id)
        assert d.value(DCT.title) == Literal(dataset.title)
        assert d.value(DCT.issued) == Literal(dataset.created_at)
        assert d.value(DCT.modified) == Literal(dataset.last_modified)
        assert d.value(DCAT.landingPage) is None

    def test_all_dataset_fields(self, app):
        resources = ResourceFactory.build_batch(3)
        org = OrganizationFactory(name="organization")
        contact = ContactPointFactory(
            name="Organization contact",
            email="hello@its.me",
            contact_form="https://data.support.com",
        )
        remote_url = "https://somewhere.org/dataset"
        dataset = DatasetFactory(
            tags=faker.tags(nb=3),
            resources=resources,
            frequency="daily",
            acronym="acro",
            organization=org,
            contact_point=contact,
            harvest=HarvestDatasetMetadata(
                remote_url=remote_url, dct_identifier="foobar-identifier"
            ),
        )
        app.config["SITE_TITLE"] = "Test site title"
        d = dataset_to_rdf(dataset)
        g = d.graph

        assert isinstance(d, RdfResource)
        assert len(list(g.subjects(RDF.type, DCAT.Dataset))) == 1

        assert g.value(d.identifier, RDF.type) == DCAT.Dataset

        assert isinstance(d.identifier, URIRef)
        uri = url_for("api.dataset", dataset=dataset.id, _external=True)
        assert str(d.identifier) == uri
        assert d.value(DCT.identifier) == Literal("foobar-identifier")
        alternate_identifier = d.value(ADMS.identifier)
        assert alternate_identifier.value(RDF.type).identifier == ADMS.Identifier
        assert f"datasets/{dataset.id}" in alternate_identifier.value(SKOS.notation)
        assert alternate_identifier.value(DCT.creator) == Literal("Test site title")
        assert d.value(DCT.title) == Literal(dataset.title)
        assert d.value(SKOS.altLabel) == Literal(dataset.acronym)
        assert d.value(DCT.description) == Literal(dataset.description)
        assert d.value(DCT.issued) == Literal(dataset.created_at)
        assert d.value(DCT.modified) == Literal(dataset.last_modified)
        assert d.value(DCT.accrualPeriodicity).identifier == FREQ.daily
        assert d.value(DCAT.landingPage).identifier == URIRef(remote_url)
        expected_tags = set(Literal(t) for t in dataset.tags)
        assert set(d.objects(DCAT.keyword)) == expected_tags
        assert len(list(d.objects(DCAT.distribution))) == len(resources)
        org = d.value(DCT.publisher)
        assert org.value(RDF.type).identifier == FOAF.Organization
        assert org.value(FOAF.name) == Literal("organization")
        contact_rdf = d.value(DCAT.contactPoint)
        assert contact_rdf.value(RDF.type).identifier == VCARD.Kind
        assert contact_rdf.value(VCARD.fn) == Literal("Organization contact")
        assert contact_rdf.value(VCARD.hasEmail).identifier == URIRef("mailto:hello@its.me")
        assert contact_rdf.value(VCARD.hasUrl).identifier == URIRef("https://data.support.com")

    def test_map_unkownn_frequencies(self):
        assert frequency_to_rdf("hourly") == FREQ.continuous

        assert frequency_to_rdf("fourTimesADay") == FREQ.daily
        assert frequency_to_rdf("threeTimesADay") == FREQ.daily
        assert frequency_to_rdf("semidaily") == FREQ.daily

        assert frequency_to_rdf("fourTimesAWeek") == FREQ.threeTimesAWeek

        assert frequency_to_rdf("punctual") is None
        assert frequency_to_rdf("unknown") is None

        assert frequency_to_rdf("quinquennial") is None  # Better idea ?

    def test_minimal_resource_fields(self):
        resource = ResourceFactory()

        r = resource_to_rdf(resource)
        graph = r.graph
        distribs = graph.subjects(RDF.type, DCAT.Distribution)

        assert isinstance(r, RdfResource)
        assert len(list(distribs)) == 1

        assert graph.value(r.identifier, RDF.type) == DCAT.Distribution
        assert r.value(DCT.title) == Literal(resource.title)
        assert r.value(DCAT.downloadURL).identifier == URIRef(resource.url)
        assert r.value(DCT.issued) == Literal(resource.created_at)
        assert r.value(DCT.modified) == Literal(resource.last_modified)

    def test_all_resource_fields(self):
        license = LicenseFactory()
        resource = ResourceFactory(format="csv")
        dataset = DatasetFactory(resources=[resource], license=license)
        permalink = url_for("api.resource_redirect", id=resource.id, _external=True)

        r = resource_to_rdf(resource, dataset)

        assert r.value(DCT.title) == Literal(resource.title)
        assert r.value(DCT.description) == Literal(resource.description)
        assert r.value(DCT.issued) == Literal(resource.created_at)
        assert r.value(DCT.modified) == Literal(resource.last_modified)
        assert r.value(DCT.license).identifier == URIRef(license.url)
        assert r.value(DCT.rights) == Literal(license.title)
        assert r.value(DCAT.downloadURL).identifier == URIRef(resource.url)
        assert r.value(DCAT.accessURL).identifier == URIRef(permalink)
        assert r.value(DCAT.byteSize) == Literal(resource.filesize)
        assert r.value(DCAT.mediaType) == Literal(resource.mime)
        assert r.value(DCT.format) == Literal(resource.format)

        checksum = r.value(SPDX.checksum)
        assert r.graph.value(checksum.identifier, RDF.type) == SPDX.Checksum
        assert r.graph.value(checksum.identifier, SPDX.algorithm) == SPDX.checksumAlgorithm_sha1
        assert checksum.value(SPDX.checksumValue) == Literal(resource.checksum.value)

    def test_temporal_coverage(self):
        start = faker.past_date(start_date="-30d")
        end = faker.future_date(end_date="+30d")
        temporal_coverage = db.DateRange(start=start, end=end)
        dataset = DatasetFactory(temporal_coverage=temporal_coverage)

        d = dataset_to_rdf(dataset)

        pot = d.value(DCT.temporal)

        assert pot.value(RDF.type).identifier == DCT.PeriodOfTime
        assert pot.value(DCAT.startDate).toPython() == start
        assert pot.value(DCAT.endDate).toPython() == end

    def test_from_external_repository(self):
        dataset = DatasetFactory(
            harvest=HarvestDatasetMetadata(
                dct_identifier="an-identifier", uri="https://somewhere.org/dataset"
            )
        )

        d = dataset_to_rdf(dataset)

        assert isinstance(d.identifier, URIRef)
        assert str(d.identifier) == "https://somewhere.org/dataset"
        assert d.value(DCT.identifier) == Literal("an-identifier")

    def test_hvd_dataset(self):
        """Test that a dataset tagged hvd has appropriate DCAT-AP HVD properties"""
        dataset = DatasetFactory(
            resources=ResourceFactory.build_batch(3), tags=["hvd", "mobilite", "test"]
        )
        d = dataset_to_rdf(dataset)

        assert d.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)
        assert d.value(DCATAP.hvdCategory).identifier == URIRef(
            TAG_TO_EU_HVD_CATEGORIES["mobilite"]
        )
        for distrib in d.objects(DCAT.distribution):
            assert distrib.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)


@pytest.mark.usefixtures("clean_db")
class RdfToDatasetTest:
    def test_minimal(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.title == title

    def test_update(self):
        original = DatasetFactory()

        node = URIRef("https://test.org/dataset")
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(new_title)))

        dataset = dataset_from_rdf(g, dataset=original)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.id == original.id
        assert dataset.title == new_title

    def test_minimal_from_multiple(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))

        for i in range(3):
            other = BNode()
            g.add((other, RDF.type, DCAT.Dataset))
            g.add((other, DCT.title, Literal(faker.sentence())))

        dataset = dataset_from_rdf(g, node=node)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.title == title

    def test_update_from_multiple(self):
        original = DatasetFactory()

        node = URIRef("https://test.org/dataset")
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(new_title)))

        for i in range(3):
            other = BNode()
            g.add((other, RDF.type, DCAT.Dataset))
            g.add((other, DCT.title, Literal(faker.sentence())))

        dataset = dataset_from_rdf(g, dataset=original, node=node)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.id == original.id
        assert dataset.title == new_title

    def test_all_fields(self):
        uri = "https://test.org/dataset"
        node = URIRef(uri)
        g = Graph()

        id = faker.uuid4()
        title = faker.sentence()
        acronym = faker.word()
        description = faker.paragraph()
        tags = faker.tags(nb=3)
        start = faker.past_date(start_date="-30d")
        end = faker.future_date(end_date="+30d")
        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.identifier, Literal(id)))
        g.set((node, DCT.title, Literal(title)))
        g.set((node, SKOS.altLabel, Literal(acronym)))
        g.set((node, DCT.description, Literal(description)))
        g.set((node, DCT.accrualPeriodicity, FREQ.daily))
        pot = BNode()
        g.add((node, DCT.temporal, pot))
        g.set((pot, RDF.type, DCT.PeriodOfTime))
        g.set((pot, DCAT.startDate, Literal(start)))
        g.set((pot, DCAT.endDate, Literal(end)))
        for tag in tags:
            g.add((node, DCAT.keyword, Literal(tag)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.title == title
        assert dataset.acronym == acronym
        assert dataset.description == description
        assert dataset.frequency == "daily"
        assert set(dataset.tags) == set(tags)
        assert isinstance(dataset.temporal_coverage, db.DateRange)
        assert dataset.temporal_coverage.start == start
        assert dataset.temporal_coverage.end == end

        assert dataset.harvest.dct_identifier == id
        assert dataset.harvest.uri == uri

    def test_html_description(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.identifier, Literal(faker.uuid4())))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCT.description, Literal("<div>a description</div>")))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert dataset.description == "a description"

    def test_theme_and_tags(self):
        node = BNode()
        g = Graph()

        tags = faker.tags(nb=3)
        themes = faker.tags(nb=3)
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        for tag in tags:
            g.add((node, DCAT.keyword, Literal(tag)))
        for theme in themes:
            g.add((node, DCAT.theme, Literal(theme)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert set(dataset.tags) == set(tags + themes)

    @pytest.mark.parametrize("freq,expected", FREQ_SAMPLE)
    def test_parse_dublin_core_frequencies(self, freq, expected):
        assert frequency_from_rdf(freq) == expected

    @pytest.mark.parametrize("freq,expected", FREQ_SAMPLE)
    def test_parse_dublin_core_frequencies_as_resource(self, freq, expected):
        g = Graph()
        resource = RdfResource(g, freq)
        assert frequency_from_rdf(resource) == expected

    @pytest.mark.parametrize("freq,expected", FREQ_SAMPLE)
    def test_parse_dublin_core_frequencies_as_url(self, freq, expected):
        assert frequency_from_rdf(str(freq)) == expected

    @pytest.mark.parametrize("freq,expected", EU_RDF_REQUENCIES.items())
    def test_parse_european_frequencies(self, freq, expected):
        assert frequency_from_rdf(freq) == expected

    @pytest.mark.parametrize("freq,expected", EU_RDF_REQUENCIES.items())
    def test_parse_european_frequencies_as_resource(self, freq, expected):
        g = Graph()
        resource = RdfResource(g, freq)
        assert frequency_from_rdf(resource) == expected

    @pytest.mark.parametrize("freq,expected", EU_RDF_REQUENCIES.items())
    def test_parse_european_frequencies_as_url(self, freq, expected):
        assert frequency_from_rdf(str(freq)) == expected

    def test_minimal_resource_fields(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCAT.downloadURL, Literal(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        assert isinstance(resource, Resource)
        assert resource.title == title
        assert resource.url == url

    def test_all_resource_fields(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        description = faker.paragraph()
        filesize = faker.pyint()
        issued = faker.date_time_between(start_date="-60d", end_date="-30d")
        modified = faker.past_datetime(start_date="-30d")
        mime = faker.mime_type()
        sha1 = faker.sha1()

        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCT.description, Literal(description)))
        g.add((node, DCAT.downloadURL, Literal(url)))
        g.add((node, DCT.issued, Literal(issued)))
        g.add((node, DCT.modified, Literal(modified)))
        g.add((node, DCAT.byteSize, Literal(filesize)))
        g.add((node, DCAT.mediaType, Literal(mime)))
        g.add((node, DCT.format, Literal("CSV")))

        checksum = BNode()
        g.add((node, SPDX.checksum, checksum))
        g.add((checksum, RDF.type, SPDX.Checksum))
        g.add((checksum, SPDX.algorithm, SPDX.checksumAlgorithm_sha1))
        g.add((checksum, SPDX.checksumValue, Literal(sha1)))

        resource = resource_from_rdf(g)
        resource.validate()

        assert isinstance(resource, Resource)
        assert resource.title == title
        assert resource.url == url
        assert resource.description == description
        assert resource.filesize == filesize
        assert resource.mime == mime
        assert isinstance(resource.checksum, Checksum)
        assert resource.checksum.type == "sha1"
        assert resource.checksum.value == sha1
        assert resource.harvest.created_at.date() == issued.date()
        assert resource.harvest.modified_at.date() == modified.date()
        assert resource.format == "csv"

    def test_download_url_over_access_url(self):
        node = BNode()
        g = Graph()

        access_url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCAT.accessURL, Literal(access_url)))

        resource = resource_from_rdf(g)
        resource.validate()
        assert resource.url == access_url

        download_url = faker.uri()
        g.add((node, DCAT.downloadURL, Literal(download_url)))

        resource = resource_from_rdf(g)
        resource.validate()
        assert resource.url == download_url

    def test_resource_html_description(self):
        node = BNode()
        g = Graph()

        description = faker.paragraph()
        html_description = "<div>{0}</div>".format(description)
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCT.description, Literal(html_description)))
        g.add((node, DCAT.downloadURL, Literal(faker.uri())))

        resource = resource_from_rdf(g)
        resource.validate()

        assert resource.description == description

    def test_resource_title_from_url(self):
        node = BNode()
        g = Graph()
        url = "https://www.somewhere.com/somefile.csv"

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        assert resource.title == "somefile.csv"

    def test_resource_title_from_format(self):
        node = BNode()
        g = Graph()
        url = "https://www.somewhere.com/no-extension/"

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))
        g.set((node, DCT.format, Literal("CSV")))

        resource = resource_from_rdf(g)
        resource.validate()

        assert resource.title == _("{format} resource").format(format="csv")

    def test_resource_generic_title(self):
        node = BNode()
        g = Graph()
        url = "https://www.somewhere.com/no-extension/"

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        assert resource.title == _("Nameless resource")

    def test_resource_title_ignore_dynamic_url(self):
        node = BNode()
        g = Graph()
        url = "https://www.somewhere.com/endpoint.json?param=value"

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        assert resource.title == _("Nameless resource")

    def test_match_existing_resource_by_url(self):
        dataset = DatasetFactory(resources=ResourceFactory.build_batch(3))
        existing_resource = dataset.resources[1]
        node = BNode()
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(new_title)))
        g.add((node, DCAT.downloadURL, Literal(existing_resource.url)))

        resource = resource_from_rdf(g, dataset)
        resource.validate()

        assert isinstance(resource, Resource)
        assert resource.title == new_title
        assert resource.id == existing_resource.id

    def test_can_extract_from_rdf_resource(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCAT.downloadURL, Literal(url)))

        resource = resource_from_rdf(g.resource(node))
        resource.validate()

        assert isinstance(resource, Resource)
        assert resource.title == title
        assert resource.url == url

    def test_dataset_has_resources(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        for i in range(3):
            rnode = BNode()
            g.set((rnode, RDF.type, DCAT.Distribution))
            g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
            g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert len(dataset.resources) == 3

    def test_dataset_has_resources_from_buggy_plural_distribution(self):
        """Try to extract resources from the wrong distributions attribute"""
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.add((node, DCAT.distributions, rnode))  # use plural name

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert len(dataset.resources) == 1

    def test_dataset_has_resources_from_literal_instead_of_uriref(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        # Resource URL is expressed as a Literal
        g.set((rnode, DCAT.downloadURL, Literal(faker.uri())))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset, Dataset)
        assert len(dataset.resources) == 1

    def test_match_license_from_license_uri(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, URIRef(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset.license, License)
        assert dataset.license == license

    def test_match_license_from_rights_uri(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.rights, URIRef(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)

        assert isinstance(dataset.license, License)
        assert dataset.license == license

    def test_match_license_from_license_uri_literal(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, Literal(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset.license, License)
        assert dataset.license == license

    def test_match_license_from_license_title(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, Literal(license.title)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        assert isinstance(dataset.license, License)
        assert dataset.license == license

    def test_parse_temporal_as_schema_format(self):
        node = BNode()
        g = Graph()
        start = faker.past_date(start_date="-30d")
        end = faker.future_date(end_date="+30d")

        g.set((node, RDF.type, DCT.PeriodOfTime))
        g.set((node, SCHEMA.startDate, Literal(start)))
        g.set((node, SCHEMA.endDate, Literal(end)))

        daterange = temporal_from_rdf(g.resource(node))

        assert isinstance(daterange, db.DateRange)
        assert daterange.start == start
        assert daterange.end == end

    def test_parse_temporal_as_iso_interval(self):
        start = faker.past_date(start_date="-30d")
        end = faker.future_date(end_date="+30d")

        pot = Literal("{0}/{1}".format(start.isoformat(), end.isoformat()))

        daterange = temporal_from_rdf(pot)

        assert isinstance(daterange, db.DateRange)
        assert daterange.start == start
        assert daterange.end == end

    def test_parse_temporal_as_iso_year(self):
        pot = Literal("2017")

        daterange = temporal_from_rdf(pot)

        assert isinstance(daterange, db.DateRange)
        assert daterange.start, date(2017, 1 == 1)
        assert daterange.end, date(2017, 12 == 31)

    def test_parse_temporal_as_iso_month(self):
        pot = Literal("2017-06")

        daterange = temporal_from_rdf(pot)

        assert isinstance(daterange, db.DateRange)
        assert daterange.start, date(2017, 6 == 1)
        assert daterange.end, date(2017, 6 == 30)

    @pytest.mark.skipif(not GOV_UK_REF_IS_UP, reason="Gov.uk references is unreachable")
    def test_parse_temporal_as_gov_uk_format(self):
        node = URIRef("http://reference.data.gov.uk/id/year/2017")
        g = Graph()

        g.set((node, RDF.type, DCT.PeriodOfTime))

        daterange = temporal_from_rdf(g.resource(node))

        assert isinstance(daterange, db.DateRange)
        assert daterange.start, date(2017, 1 == 1)
        assert daterange.end, date(2017, 12 == 31)

    def test_parse_temporal_is_failsafe(self):
        node = URIRef("http://nowhere.org")
        g = Graph()

        g.set((node, RDF.type, DCT.PeriodOfTime))

        assert temporal_from_rdf(g.resource(node)) is None
        assert temporal_from_rdf(Literal("unparseable")) is None

    def test_unicode(self):
        g = Graph()
        title = "ééé"
        description = "éééé"

        node = BNode()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCT.description, Literal(description)))

        rnode = BNode()
        g.add((rnode, RDF.type, DCAT.Distribution))
        g.add((rnode, DCT.title, Literal(title)))
        g.add((rnode, DCT.description, Literal(description)))
        g.add((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()
        assert dataset.title == title
        assert dataset.description == description

        resource = dataset.resources[0]
        assert resource.title == title
        assert resource.description == description

    def test_primary_topic_identifier_from_rdf_outer(self):
        """Check that a CatalogRecord node that is primaryTopic of a dataset is found and parsed"""
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))

        primary_topic_node = BNode()
        g.add((primary_topic_node, RDF.type, DCAT.CatalogRecord))
        g.add((primary_topic_node, DCT.identifier, Literal("primary-topic-identifier")))
        g.add((primary_topic_node, FOAF.primaryTopic, node))

        pti = primary_topic_identifier_from_rdf(g, g.resource(node))
        assert pti == Literal("primary-topic-identifier")

    def test_primary_topic_identifier_from_rdf_inner(self):
        """Check that a nested isPrimaryTopicOf of a dataset is found and parsed"""
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))

        primary_topic_node = BNode()
        g.add((primary_topic_node, RDF.type, DCAT.CatalogRecord))
        g.add((primary_topic_node, DCT.identifier, Literal("primary-topic-identifier")))

        g.add((node, FOAF.isPrimaryTopicOf, primary_topic_node))

        pti = primary_topic_identifier_from_rdf(g, g.resource(node))
        assert pti == Literal("primary-topic-identifier")


@pytest.mark.frontend
class DatasetRdfViewsTest:
    def test_rdf_default_to_jsonld(self, client):
        dataset = DatasetFactory()
        expected = url_for("api.dataset_rdf_format", dataset=dataset.id, format="json")
        response = client.get(url_for("api.dataset_rdf", dataset=dataset))
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation(self, client):
        dataset = DatasetFactory()
        expected = url_for("api.dataset_rdf_format", dataset=dataset.id, format="xml")
        url = url_for("api.dataset_rdf", dataset=dataset)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers)
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation_response(self, client):
        """Check we have valid XML as output"""
        dataset = DatasetFactory()
        url = url_for("api.dataset_rdf", dataset=dataset)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers, follow_redirects=True)
        element = XML(response.data)
        assert element.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"

    def test_dataset_rdf_json_ld(self, client):
        dataset = DatasetFactory()
        for fmt in "json", "jsonld":
            url = url_for("api.dataset_rdf_format", dataset=dataset, format=fmt)
            response = client.get(url, headers={"Accept": "application/ld+json"})
            assert200(response)
            assert response.content_type == "application/ld+json"
            assert response.json["@context"]["@vocab"] == "http://www.w3.org/ns/dcat#"

    @pytest.mark.parametrize(
        "fmt,mime",
        [
            ("n3", "text/n3"),
            ("nt", "application/n-triples"),
            ("ttl", "application/x-turtle"),
            ("xml", "application/rdf+xml"),
            ("rdf", "application/rdf+xml"),
            ("owl", "application/rdf+xml"),
            ("trig", "application/trig"),
        ],
    )
    def test_dataset_rdf_formats(self, client, fmt, mime):
        dataset = DatasetFactory()
        url = url_for("api.dataset_rdf_format", dataset=dataset, format=fmt)
        response = client.get(url, headers={"Accept": mime})
        assert200(response)
        assert response.content_type == mime


class DatasetFromRdfUtilsTest:
    def test_licenses_from_rdf(self):
        """Test a bunch of cases of licenses detection from RDF"""
        rdf_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
            <rdf:RDF
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
            xmlns:foaf="http://xmlns.com/foaf/0.1/"
            xmlns:dct="http://purl.org/dc/terms/"
            xmlns:cc="http://creativecommons.org/ns#"
            xmlns:ex="http://example.org/">

            <rdf:Description rdf:about="http://example.org/dataset1">
                <dct:title>Comprehensive License Example Dataset</dct:title>
                <dct:license rdf:resource="http://example.org/custom-license"/>
                <dct:license>This is a literal license statement</dct:license>
                <dct:license>
                    <rdf:Description>
                        <rdfs:label>Embedded License Description</rdfs:label>
                    </rdf:Description>
                </dct:license>
                <dct:license
                    xmlns:dct="http://purl.org/dc/terms/"
                    rdf:resource="http://inspire.ec.europa.eu/metadata-codelist/ConditionsApplyingToAccessAndUse/noConditionsApply"
                >
                    No conditions apply to access and use.
                </dct:license>
                <dct:license rdf:resource="https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf"/>
            </rdf:Description>

            <rdf:Description rdf:about="http://example.org/custom-license">
                <rdfs:label>Custom Organizational License</rdfs:label>
                <dct:description>A license specific to our organization</dct:description>
            </rdf:Description>

            </rdf:RDF>
        """
        g = Graph()
        g.parse(data=rdf_xml_data, format="xml")
        ex = Namespace("http://example.org/")
        dataset = RdfResource(g, ex.dataset1)
        licences = licenses_from_rdf(dataset)
        expected_licences = set(
            [
                "Custom Organizational License",
                "This is a literal license statement",
                "Embedded License Description",
                "https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf",
                "http://inspire.ec.europa.eu/metadata-codelist/ConditionsApplyingToAccessAndUse/noConditionsApply",
            ]
        )
        assert expected_licences == licences
