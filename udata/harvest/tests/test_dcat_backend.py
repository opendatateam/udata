import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import date

import pytest
from flask import current_app
from lxml import etree
from rdflib import Graph

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import LicenseFactory, ResourceSchemaMockData
from udata.core.dataset.rdf import dataset_from_rdf
from udata.core.organization.factories import OrganizationFactory
from udata.harvest.models import HarvestJob
from udata.models import Dataset
from udata.rdf import DCAT, RDF, namespace_manager
from udata.storage.s3 import get_from_json

from .. import actions
from ..backends.dcat import URIS_TO_REPLACE, CswIso19139DcatBackend
from .factories import HarvestSourceFactory

log = logging.getLogger(__name__)


TEST_DOMAIN = "data.test.org"  # Need to be used in fixture file
DCAT_URL_PATTERN = "http://{domain}/{path}"
DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), "dcat")
CSW_DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), "csw_dcat")


def mock_dcat(rmock, filename, path=None):
    url = DCAT_URL_PATTERN.format(path=path or filename, domain=TEST_DOMAIN)
    with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
        body = dcatfile.read()
    rmock.get(url, text=body)
    return url


def mock_pagination(rmock, path, pattern):
    url = DCAT_URL_PATTERN.format(path=path, domain=TEST_DOMAIN)

    def callback(request, context):
        page = request.qs.get("page", [1])[0]
        filename = pattern.format(page=page)
        context.status_code = 200
        with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
            return dcatfile.read()

    rmock.get(rmock.ANY, text=callback)
    return url


def mock_csw_pagination(rmock, path, pattern):
    url = DCAT_URL_PATTERN.format(path=path, domain=TEST_DOMAIN)

    def callback(request, context):
        request_tree = ET.fromstring(request.body)
        page = int(request_tree.get("startPosition"))
        with open(os.path.join(CSW_DCAT_FILES_DIR, pattern.format(page))) as cswdcatfile:
            return cswdcatfile.read()

    rmock.post(rmock.ANY, text=callback)
    return url


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(PLUGINS=["dcat"])
class DcatBackendTest:
    def test_simple_flat(self, rmock):
        filename = "flat.jsonld"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 3

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 3

        for i in "1 2 3".split():
            d = datasets[i]
            assert d.title == f"Dataset {i}"
            assert d.description == f"Dataset {i} description"
            assert d.harvest.remote_id == i
            assert d.harvest.backend == "DCAT"
            assert d.harvest.source_id == str(source.id)
            assert d.harvest.domain == source.domain
            assert d.harvest.dct_identifier == i
            assert d.harvest.remote_url == f"http://data.test.org/datasets/{i}"
            assert d.harvest.uri == f"http://data.test.org/datasets/{i}"
            assert d.harvest.created_at.date() == date(2016, 12, 14)
            assert d.harvest.modified_at.date() == date(2016, 12, 14)
            assert d.harvest.last_update.date() == date.today()
            assert d.harvest.archived_at is None
            assert d.harvest.archived is None

        # First dataset
        dataset = datasets["1"]
        assert dataset.tags == ["tag-1", "tag-2", "tag-3", "tag-4", "theme-1", "theme-2"]
        assert len(dataset.resources) == 2

        # Second dataset
        dataset = datasets["2"]
        assert dataset.tags == ["tag-1", "tag-2", "tag-3"]
        assert len(dataset.resources) == 2

        # Third dataset
        dataset = datasets["3"]
        assert dataset.tags == ["tag-1", "tag-2"]
        assert len(dataset.resources) == 1

    def test_flat_with_blank_nodes(self, rmock):
        filename = "bnodes.jsonld"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 3
        assert len(datasets["1"].resources) == 2
        assert len(datasets["2"].resources) == 2
        assert len(datasets["3"].resources) == 1

        assert datasets["1"].resources[0].title == "Resource 1-1"
        assert datasets["1"].resources[0].description == "A JSON resource"
        assert datasets["1"].resources[0].format == "json"
        assert datasets["1"].resources[0].mime == "application/json"

    @pytest.mark.options(
        SCHEMA_CATALOG_URL="https://example.com/schemas",
        HARVEST_MAX_CATALOG_SIZE_IN_MONGO=None,
        HARVEST_GRAPHS_S3_BUCKET="test_bucket",
        S3_URL="https://example.org",
        S3_ACCESS_KEY_ID="myUser",
        S3_SECRET_ACCESS_KEY="password",
    )
    def test_flat_with_blank_nodes_xml(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 3
        assert len(datasets["3"].resources) == 1
        assert len(datasets["1"].resources) == 2
        assert len(datasets["2"].resources) == 2

    def test_harvest_dataservices(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        dataservices = Dataservice.objects

        assert len(dataservices) == 1
        assert dataservices[0].title == "Explore API v2"
        assert dataservices[0].base_api_url == "https://data.paris2024.org/api/explore/v2.1/"
        assert (
            dataservices[0].endpoint_description_url
            == "https://data.paris2024.org/api/explore/v2.1/swagger.json"
        )
        assert (
            dataservices[0].harvest.remote_url
            == "https://data.paris2024.org/api/explore/v2.1/console"
        )

    def test_harvest_literal_spatial(self, rmock):
        url = mock_dcat(rmock, "evian.json")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}
        assert len(datasets) == 8
        assert (
            datasets[
                "https://www.arcgis.com/home/item.html?id=f6565516d1354383b25793e630cf3f2b&sublayer=5"
            ].spatial
            is not None
        )
        assert datasets[
            "https://www.arcgis.com/home/item.html?id=f6565516d1354383b25793e630cf3f2b&sublayer=5"
        ].spatial.geom == {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [6.5735, 46.3912],
                        [6.6069, 46.3912],
                        [6.6069, 46.4028],
                        [6.5735, 46.4028],
                        [6.5735, 46.3912],
                    ]
                ]
            ],
        }

    @pytest.mark.skip(
        reason="Mocking S3 requires `moto` which is not available for our current Python 3.7. We can manually test it."
    )
    @pytest.mark.options(
        SCHEMA_CATALOG_URL="https://example.com/schemas", HARVEST_JOBS_RETENTION_DAYS=0
    )
    # @mock_s3
    # @pytest.mark.options(HARVEST_MAX_CATALOG_SIZE_IN_MONGO=15, HARVEST_GRAPHS_S3_BUCKET="test_bucket", S3_URL="https://example.org", S3_ACCESS_KEY_ID="myUser", S3_SECRET_ACCESS_KEY="password")
    def test_harvest_big_catalog(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        # We need to create the bucket since this is all in Moto's 'virtual' AWS account
        # conn = boto3.resource(
        #     "s3",
        #     endpoint_url="https://example.org",
        #     aws_access_key_id="myUser",
        #     aws_secret_access_key="password",
        # )
        # conn.create_bucket(Bucket="test_bucket")

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert datasets["1"].schema is None
        resources_by_title = {resource["title"]: resource for resource in datasets["1"].resources}

        # Schema with wrong version are considered as external. Maybe we could change this in the future
        assert (
            resources_by_title["Resource 1-2"].schema.url
            == "https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/1337.42.0/schema-statique.json"
        )
        assert resources_by_title["Resource 1-2"].schema.name is None
        assert resources_by_title["Resource 1-2"].schema.version is None

        assert datasets["2"].schema.name == "RGF93 / Lambert-93 (EPSG:2154)"
        assert (
            datasets["2"].schema.url
            == "http://inspire.ec.europa.eu/glossary/SpatialReferenceSystem"
        )
        resources_by_title = {resource["title"]: resource for resource in datasets["2"].resources}

        # Unknown schema are kept as they were provided
        assert resources_by_title["Resource 2-1"].schema.name == "Example Schema"
        assert resources_by_title["Resource 2-1"].schema.url == "https://example.org/schema.json"
        assert resources_by_title["Resource 2-1"].schema.version is None

        assert resources_by_title["Resource 2-2"].schema is None

        assert datasets["3"].schema is None
        resources_by_title = {resource["title"]: resource for resource in datasets["3"].resources}

        # If there is just the URL, and it matches a known schema inside the catalog, only set the name and the version
        # (discard the URL)
        assert resources_by_title["Resource 3-1"].schema.name == "etalab/schema-irve-statique"
        assert resources_by_title["Resource 3-1"].schema.url is None
        assert resources_by_title["Resource 3-1"].schema.version == "2.2.0"

        job = HarvestJob.objects.order_by("-id").first()

        assert job.source.slug == source.slug
        assert (
            get_from_json(current_app.config.get("HARVEST_GRAPHS_S3_BUCKET"), job.data["filename"])
            is not None
        )

        # Retention is 0 days in config
        actions.purge_jobs()
        assert (
            get_from_json(current_app.config.get("HARVEST_GRAPHS_S3_BUCKET"), job.data["filename"])
            is None
        )

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas", HARVEST_MAX_ITEMS=2)
    def test_harvest_max_items(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        assert Dataset.objects.count() == 2
        assert HarvestJob.objects.first().status == "done"

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_harvest_spatial(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert datasets["1"].spatial is None
        assert datasets["2"].spatial.geom == {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-6, 51], [10, 51], [10, 40], [-6, 40], [-6, 51]]],
                [[[4, 45], [4, 46], [4, 46], [4, 45], [4, 45]]],
                [[[159, -25.0], [159, -11], [212, -11], [212, -25.0], [159, -25.0]]],
            ],
        }
        assert datasets["3"].spatial is None

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_harvest_schemas(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        filename = "bnodes.xml"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert datasets["1"].schema is None
        resources_by_title = {resource["title"]: resource for resource in datasets["1"].resources}

        # Schema with wrong version are considered as external. Maybe we could change this in the future
        assert (
            resources_by_title["Resource 1-2"].schema.url
            == "https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/1337.42.0/schema-statique.json"
        )
        assert resources_by_title["Resource 1-2"].schema.name is None
        assert resources_by_title["Resource 1-2"].schema.version is None

        assert datasets["2"].schema.name == "RGF93 / Lambert-93 (EPSG:2154)"
        assert (
            datasets["2"].schema.url
            == "http://inspire.ec.europa.eu/glossary/SpatialReferenceSystem"
        )
        resources_by_title = {resource["title"]: resource for resource in datasets["2"].resources}

        # Unknown schema are kept as they were provided
        assert resources_by_title["Resource 2-1"].schema.name == "Example Schema"
        assert resources_by_title["Resource 2-1"].schema.url == "https://example.org/schema.json"
        assert resources_by_title["Resource 2-1"].schema.version is None

        assert resources_by_title["Resource 2-2"].schema is None

        assert datasets["3"].schema is None
        resources_by_title = {resource["title"]: resource for resource in datasets["3"].resources}

        # If there is just the URL, and it matches a known schema inside the catalog, only set the name and the version
        # (discard the URL)
        assert resources_by_title["Resource 3-1"].schema.name == "etalab/schema-irve-statique"
        assert resources_by_title["Resource 3-1"].schema.url is None
        assert resources_by_title["Resource 3-1"].schema.version == "2.2.0"

    def test_simple_nested_attributes(self, rmock):
        filename = "nested.jsonld"
        url = mock_dcat(rmock, filename)
        source = HarvestSourceFactory(backend="dcat", url=url, organization=OrganizationFactory())

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 1

        dataset = Dataset.objects.first()
        assert dataset.temporal_coverage is not None
        assert dataset.temporal_coverage.start == date(2016, 1, 1)
        assert dataset.temporal_coverage.end == date(2016, 12, 5)
        assert dataset.harvest.remote_url == "http://data.test.org/datasets/1"

        assert len(dataset.resources) == 1

        resource = dataset.resources[0]
        assert resource.checksum is not None
        assert resource.checksum.type == "sha1"
        assert resource.checksum.value == "fb4106aa286a53be44ec99515f0f0421d4d7ad7d"

    def test_idempotence(self, rmock):
        filename = "flat.jsonld"
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        # Run the same havester twice
        actions.run(source.slug)
        actions.run(source.slug)

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 3
        assert len(datasets["1"].resources) == 2
        assert len(datasets["2"].resources) == 2
        assert len(datasets["3"].resources) == 1

    def test_hydra_partial_collection_view_pagination(self, rmock):
        url = mock_pagination(rmock, "catalog.jsonld", "partial-collection-{page}.jsonld")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 4

    def test_hydra_legacy_paged_collection_pagination(self, rmock):
        url = mock_pagination(rmock, "catalog.jsonld", "paged-collection-{page}.jsonld")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 4

    def test_failure_on_initialize(self, rmock):
        url = DCAT_URL_PATTERN.format(path="", domain=TEST_DOMAIN)
        rmock.get(url, text="should fail")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == "failed"

    def test_supported_mime_type(self, rmock):
        url = mock_dcat(rmock, "catalog.xml", path="without/extension")
        rmock.head(url, headers={"Content-Type": "application/xml; charset=utf-8"})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == "done"
        assert job.errors == []
        assert len(job.items) == 4

    def test_xml_catalog(self, rmock):
        LicenseFactory(id="lov2", title="Licence Ouverte Version 2.0")
        LicenseFactory(id="lov1", title="Licence Ouverte Version 1.0")

        url = mock_dcat(rmock, "catalog.xml", path="catalog.xml")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        # test dct:license support
        dataset = Dataset.objects.get(harvest__dct_identifier="3")
        assert dataset.license.id == "lov2"
        assert dataset.harvest.remote_url == "http://data.test.org/datasets/3"
        assert dataset.harvest.remote_id == "3"
        assert dataset.harvest.created_at.date() == date(2016, 12, 14)
        assert dataset.harvest.modified_at.date() == date(2016, 12, 14)
        assert dataset.frequency == "daily"
        assert dataset.description == "Dataset 3 description"

        assert dataset.temporal_coverage is not None
        assert dataset.temporal_coverage.start == date(2016, 1, 1)
        assert dataset.temporal_coverage.end == date(2016, 12, 5)

        assert dataset.extras["dcat"]["accessRights"] == [
            "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1e"
        ]
        assert dataset.extras["dcat"]["provenance"] == ["Description de la provenance des données"]

        assert "observation-de-la-terre-et-environnement" in dataset.tags
        assert "hvd" in dataset.tags

        dataset = Dataset.objects.get(harvest__dct_identifier="1")
        # test html abstract description support
        assert dataset.description == "# h1 title\n\n## h2 title\n\n **and bold text**"
        # test DCAT periodoftime
        assert dataset.temporal_coverage is not None
        assert dataset.temporal_coverage.start == date(2016, 1, 1)
        assert dataset.temporal_coverage.end == date(2016, 12, 5)
        assert dataset.contact_point.email == "hello@its.me"
        assert dataset.contact_point.name == "Organization contact"
        assert dataset.contact_point.contact_form == "https://data.support.com"
        assert dataset.frequency is None
        # test dct:license nested in distribution
        assert dataset.license.id == "lov1"

        assert len(dataset.resources) == 3

        resource_1 = next(res for res in dataset.resources if res.title == "Resource 1-1")
        assert resource_1.filetype == "remote"
        # Format is a IANA URI
        assert resource_1.format == "json"
        assert resource_1.mime == "application/json"
        assert resource_1.filesize == 12323
        assert resource_1.description == "A JSON resource"
        assert resource_1.url == "http://data.test.org/datasets/1/resources/1/file.json"
        assert resource_1.type == "main"

        resource_2 = next(res for res in dataset.resources if res.title == "Resource 1-2")
        assert resource_2.format == "json"
        assert resource_2.description == "A JSON resource"
        assert resource_2.url == "http://data.test.org/datasets/1/resources/2/file.json"
        assert resource_2.type == "main"

        # Make sure additionnal resource is correctly harvested
        resource_3 = next(res for res in dataset.resources if res.title == "Resource 1-3")
        assert resource_3.format == "json"
        assert resource_3.description == ""
        assert resource_3.url == "http://data.test.org/datasets/1/resources/3"
        assert resource_3.type == "other"

        # test dct:rights -> license support from dataset
        dataset = Dataset.objects.get(harvest__dct_identifier="2")
        assert dataset.license.id == "lov2"
        assert dataset.extras["dcat"]["rights"] == ["Licence Ouverte Version 2.0"]

        # test dct:rights storage in resource
        resource_2 = next(res for res in dataset.resources if res.title == "Resource 2-2")
        assert resource_2.extras["dcat"]["rights"] == ["Rights on nested resource"]

        # test different dct:accessRights on resources _not_ bubbling up to dataset
        dataset = Dataset.objects.get(harvest__dct_identifier="4")
        assert dataset.extras["dcat"].get("accessRights") is None
        # test dct:accessRights storage in resource
        for resource in dataset.resources:
            assert len(resource.extras["dcat"]["accessRights"]) == 2
            assert "Access right 4" in resource.extras["dcat"]["accessRights"]

    def test_geonetwork_xml_catalog(self, rmock):
        url = mock_dcat(rmock, "geonetwork.xml", path="catalog.xml")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)
        actions.run(source.slug)
        dataset = Dataset.objects.filter(organization=org).first()
        assert dataset is not None
        assert dataset.harvest is not None
        assert (
            dataset.harvest.remote_id
            == "0c456d2d-9548-4a2a-94ef-231d9d890ce2 https://sig.oreme.org/geonetwork/srv/resources0c456d2d-9548-4a2a-94ef-231d9d890ce2"
        )  # noqa
        assert (
            dataset.harvest.dct_identifier
            == "0c456d2d-9548-4a2a-94ef-231d9d890ce2 https://sig.oreme.org/geonetwork/srv/resources0c456d2d-9548-4a2a-94ef-231d9d890ce2"
        )  # noqa
        assert dataset.harvest.created_at.date() == date(2004, 11, 3)
        assert dataset.harvest.modified_at is None
        assert (
            dataset.harvest.uri
            == "https://sig.oreme.org/geonetwork/srv/resources/datasets/0c456d2d-9548-4a2a-94ef-231d9d890ce2 https://sig.oreme.org/geonetwork/srv/resources0c456d2d-9548-4a2a-94ef-231d9d890ce2"
        )  # noqa
        assert dataset.harvest.remote_url is None  # the uri validation failed
        assert dataset.description.startswith("Data of type chemistry")
        assert dataset.temporal_coverage is not None
        assert dataset.temporal_coverage.start == date(2004, 11, 3)
        assert dataset.temporal_coverage.end == date(2005, 3, 30)

    def test_sigoreme_xml_catalog(self, rmock):
        LicenseFactory(id="fr-lo", title="Licence ouverte / Open Licence")
        url = mock_dcat(rmock, "sig.oreme.rdf")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)
        actions.run(source.slug)
        dataset = Dataset.objects.filter(organization=org).first()

        assert dataset is not None
        assert dataset.frequency == "irregular"
        assert "gravi" in dataset.tags  # support dcat:keyword
        assert "geodesy" in dataset.tags  # support dcat:theme
        assert dataset.license.id == "fr-lo"
        assert len(dataset.resources) == 1
        assert dataset.description.startswith("Data from the 'National network")
        assert dataset.harvest is not None
        assert dataset.harvest.dct_identifier == "0437a976-cff1-4fa6-807a-c23006df2f8f"
        assert dataset.harvest.remote_id == "0437a976-cff1-4fa6-807a-c23006df2f8f"
        assert dataset.harvest.created_at is None
        assert dataset.harvest.modified_at is None
        assert (
            dataset.harvest.uri
            == "https://sig.oreme.org/geonetwork/srv/eng/catalog.search#/metadata//datasets/0437a976-cff1-4fa6-807a-c23006df2f8f"
        )  # noqa
        assert (
            dataset.harvest.remote_url
            == "https://sig.oreme.org/geonetwork/srv/eng/catalog.search#/metadata//datasets/0437a976-cff1-4fa6-807a-c23006df2f8f"
        )  # noqa
        assert dataset.harvest.last_update.date() == date.today()

    def test_user_agent_get(self, rmock):
        url = mock_dcat(rmock, "catalog.xml", path="without/extension")
        rmock.head(url, headers={"Content-Type": "application/xml; charset=utf-8"})
        get_mock = rmock.get(url)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)
        actions.run(source.slug)

        assert "User-Agent" in get_mock.last_request.headers
        assert get_mock.last_request.headers["User-Agent"] == "uData/0.1 dcat"

    def test_unsupported_mime_type(self, rmock):
        url = DCAT_URL_PATTERN.format(path="", domain=TEST_DOMAIN)
        rmock.head(url, headers={"Content-Type": "text/html; charset=utf-8"})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == "failed"
        assert len(job.errors) == 1

        error = job.errors[0]
        assert error.message == 'Unsupported mime type "text/html"'

    def test_unable_to_detect_format(self, rmock):
        url = DCAT_URL_PATTERN.format(path="", domain=TEST_DOMAIN)
        rmock.head(url, headers={"Content-Type": ""})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == "failed"
        assert len(job.errors) == 1

        error = job.errors[0]
        expected = "Unable to detect format from extension or mime type"
        assert error.message == expected

    def test_use_replaced_uris(self, rmock, mocker):
        mocker.patch.dict(
            URIS_TO_REPLACE,
            {
                "http://example.org/this-url-does-not-exist": "https://json-ld.org/contexts/person.jsonld"
            },
        )
        url = DCAT_URL_PATTERN.format(path="", domain=TEST_DOMAIN)
        rmock.get(
            url,
            json={
                "@context": "http://example.org/this-url-does-not-exist",
                "@type": "dcat:Catalog",
                "dataset": [],
            },
        )
        rmock.head(url, headers={"Content-Type": "application/json"})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="dcat", url=url, organization=org)
        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 0
        assert job.status == "done"

    def test_target_404(self, rmock):
        filename = "obvious-format.jsonld"
        url = DCAT_URL_PATTERN.format(path=filename, domain=TEST_DOMAIN)
        rmock.get(url, status_code=404)

        source = HarvestSourceFactory(backend="dcat", url=url, organization=OrganizationFactory())
        actions.run(source.slug)
        source.reload()

        job = source.get_last_job()
        assert job.status == "failed"
        assert len(job.errors) == 1
        assert "404 Client Error" in job.errors[0].message

        filename = "need-to-head-to-guess-format"
        url = DCAT_URL_PATTERN.format(path=filename, domain=TEST_DOMAIN)
        rmock.head(url, status_code=404)

        source = HarvestSourceFactory(backend="dcat", url=url, organization=OrganizationFactory())
        actions.run(source.slug)
        source.reload()

        job = source.get_last_job()
        assert job.status == "failed"
        assert len(job.errors) == 1
        assert "404 Client Error" in job.errors[0].message


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(PLUGINS=["csw"])
class CswDcatBackendTest:
    def test_geonetworkv4(self, rmock):
        url = mock_csw_pagination(rmock, "geonetwork/srv/eng/csw.rdf", "geonetworkv4-page-{}.xml")
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="csw-dcat", url=url, organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 6

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 6

        # First dataset
        dataset = datasets["https://www.geo2france.fr/2017/accidento"]
        assert dataset.title == "Localisation des accidents de la circulation routière en 2017"
        assert (
            dataset.description == "Accidents corporels de la circulation en Hauts de France (2017)"
        )
        assert set(dataset.tags) == set(
            [
                "donnee-ouverte",
                "accidentologie",
                "accident",
                "reseaux-de-transport",
                "accident-de-la-route",
                "hauts-de-france",
                "nord",
                "pas-de-calais",
                "oise",
                "somme",
                "aisne",
            ]
        )
        assert dataset.harvest.created_at.date() == date(2017, 1, 1)
        assert len(dataset.resources) == 1
        resource = dataset.resources[0]
        assert resource.title == "accidento_hdf_L93"
        assert resource.url == "https://www.geo2france.fr/geoserver/cr_hdf/ows"
        assert resource.format == "ogc:wms"

    def test_user_agent_post(self, rmock):
        url = mock_csw_pagination(rmock, "geonetwork/srv/eng/csw.rdf", "geonetworkv4-page-{}.xml")
        get_mock = rmock.post(url)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend="csw-dcat", url=url, organization=org)

        actions.run(source.slug)

        assert "User-Agent" in get_mock.last_request.headers
        assert get_mock.last_request.headers["User-Agent"] == "uData/0.1 csw-dcat"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(PLUGINS=["csw"])
class CswIso19139DcatBackendTest:
    @pytest.mark.parametrize(
        "remote_url_prefix",
        [
            None,
            # trailing slash
            "http://catalogue.geo-ide.developpement-durable.gouv.fr/catalogue/srv/fre/catalog.search#/metadata/",
            # no trailing slash
            "http://catalogue.geo-ide.developpement-durable.gouv.fr/catalogue/srv/fre/catalog.search#/metadata",
        ],
    )
    def test_geo2france(self, rmock, remote_url_prefix: str):
        with open(os.path.join(CSW_DCAT_FILES_DIR, "XSLT.xml"), "r") as f:
            xslt = f.read()
        url = mock_csw_pagination(rmock, "geonetwork/srv/eng/csw.rdf", "geonetwork-iso-page-{}.xml")
        rmock.get(CswIso19139DcatBackend.XSL_URL, text=xslt)
        org = OrganizationFactory()
        source = HarvestSourceFactory(
            backend="csw-iso-19139",
            url=url,
            organization=org,
            config={
                "extra_configs": [
                    {
                        "key": "remote_url_prefix",
                        "value": remote_url_prefix,
                    }
                ]
            },
        )

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 6

        datasets = {d.harvest.dct_identifier: d for d in Dataset.objects}

        assert len(datasets) == 6

        # First dataset
        # dataset identifier is gmd:RS_Identifier > gmd:codeSpace + gmd:code
        dataset = datasets[
            "http://catalogue.geo-ide.developpement-durable.gouv.fr/fr-120066022-orphan-residentifier-140d31c6-643d-42a9-85df-2737a118e144"
        ]
        assert dataset.title == "Plan local d'urbanisme de la commune de Cartigny"
        assert (
            dataset.description
            == "Le présent standard de données COVADIS concerne les documents de plans locaux d'urbanisme (PLU) et les plans d'occupation des sols (POS qui valent PLU)."
        )
        assert set(dataset.tags) == set(
            [
                "amenagement-urbanisme-zonages-planification",
                "cartigny",
                "document-durbanisme",
                "donnees-ouvertes",
                "plu",
                "usage-des-sols",
            ]
        )
        assert dataset.harvest.created_at.date() == date(2017, 10, 7)
        assert dataset.spatial.geom == {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [3.28133559, 50.48188019],
                        [1.31279111, 50.48188019],
                        [1.31279111, 49.38547516],
                        [3.28133559, 49.38547516],
                        [3.28133559, 50.48188019],
                    ]
                ]
            ],
        }
        assert (
            dataset.contact_point.name
            == "DDTM 80 (Direction Départementale des Territoires et de la Mer de la Somme)"
        )
        assert dataset.contact_point.email == "ddtm-sap-bsig@somme.gouv.fr"

        # License is not properly mapped in XSLT conversion
        assert dataset.license is None

        # Distributions don't get properly mapped to distribution with this XSLT if missing CI_OnLineFunctionCode.
        # A CI_OnLineFunctionCode was added explicitely on one of the Online Resources.
        # (See mapping at: https://semiceu.github.io/GeoDCAT-AP/releases/2.0.0/#resource-locator---on-line-resource)
        assert len(dataset.resources) == 1
        resource = dataset.resources[0]
        assert resource.title == "Téléchargement direct du lot et des documents associés"
        assert (
            resource.url
            == "http://atom.geo-ide.developpement-durable.gouv.fr/atomArchive/GetResource?id=fr-120066022-ldd-cab63273-b3ae-4e8a-ae1c-6192e45faa94&datasetAggregate=true"
        )

        # Sadly resource format is parsed as a blank node. Format parsing should be improved.
        assert re.match(r"n[0-9a-f]{32}", resource.format)

        # Computed from source config `remote_url_prefix` + `dct:identifier` from `isPrimaryTopicOf`
        if remote_url_prefix:
            assert (
                dataset.harvest.remote_url
                == "http://catalogue.geo-ide.developpement-durable.gouv.fr/catalogue/srv/fre/catalog.search#/metadata/fr-120066022-ldd-56fce164-04b2-41ae-be87-9f256f39dd44"
            )
        else:
            # this is the first dct:landingPage found in the node
            # if it breaks, it's not necessarily a bug — this acts as a demonstration of current behavior
            assert (
                dataset.harvest.remote_url
                == "https://ogc.geo-ide.developpement-durable.gouv.fr/csw/all-dataset?REQUEST=GetRecordById&SERVICE=CSW&VERSION=2.0.2&RESULTTYPE=results&elementSetName=full&TYPENAMES=gmd:MD_Metadata&OUTPUTSCHEMA=http://www.isotc211.org/2005/gmd&ID=fr-120066022-ldd-56fce164-04b2-41ae-be87-9f256f39dd44"
            )

        # accessRights is gotten from the only resource that is recognized as a distribution and copied to the dataset level
        access_right = ["Pas de restriction d'accès public selon INSPIRE"]
        assert dataset.extras["dcat"]["accessRights"] == access_right
        # also present on the resource level
        assert resource.extras["dcat"]["accessRights"] == access_right

        # see `test_geo_ide` for detailed explanation of the following
        assert dataset.extras["dcat"].get("license") is None
        assert len(resource.extras["dcat"]["license"]) == 6
        assert dataset.extras["dcat"].get("rights") is None
        assert resource.extras["dcat"].get("rights") is None

    def test_geo_ide(self):
        # this is the string used in geo-ide for now
        lov1 = LicenseFactory(
            id="lov1",
            url="http://www.data.gouv.fr/Licence-Ouverte-Open-Licence",
        )

        with open(os.path.join(CSW_DCAT_FILES_DIR, "XSLT.xml"), "rb") as f:
            xslt = f.read()
        with open(os.path.join(CSW_DCAT_FILES_DIR, "geo-ide_single-dataset.xml"), "rb") as f:
            csw = f.read()

        # apply xslt transformation manually instead of using the harvest backend since we're only processing one dataset
        transform = etree.XSLT(etree.fromstring(xslt))
        tree_before_transform = etree.fromstring(csw)
        tree = transform(tree_before_transform, CoupledResourceLookUp="'disabled'")
        subgraph = Graph(namespace_manager=namespace_manager)
        subgraph.parse(etree.tostring(tree), format="application/rdf+xml")
        node = next(subgraph.subjects(RDF.type, DCAT.Dataset))

        dataset = dataset_from_rdf(subgraph, dataset=None, node=node)
        assert dataset.title == "Plan local d'urbanisme de la commune de Combles"
        assert len(dataset.resources) == 6
        assert dataset.license == lov1

        # accessRights is retrieved from the resources
        access_right = ["Pas de restriction d'accès public selon INSPIRE"]
        assert dataset.extras["dcat"]["accessRights"] == access_right
        # also present on the resource level
        for resource in dataset.resources:
            assert resource.extras["dcat"]["accessRights"] == access_right

        # _no_ licence extra on dataset level, since they're in resources
        assert dataset.extras["dcat"].get("license") is None
        # all useLimitations have been duplicated on resources as dct:license
        for resource in dataset.resources:
            r_licenses = resource.extras["dcat"]["license"]
            assert len(r_licenses) == 6
            assert any("Licence Ouverte 1.0" in x for x in r_licenses)

        # no dct:rights anywhere, everything is in dct:license (at least for now)
        assert dataset.extras["dcat"].get("rights") is None
        for resource in dataset.resources:
            assert resource.extras["dcat"].get("rights") is None
