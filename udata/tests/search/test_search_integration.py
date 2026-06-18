import time

import pytest
from flask import url_for

from udata.core.access_type.constants import AccessType
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization import constants as org_constants
from udata.core.organization.constants import COMPANY, PUBLIC_SERVICE
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import (
    TopicElementDatasetFactory,
    TopicElementFactory,
    TopicFactory,
)
from udata.core.user.factories import UserFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import requires_search_service


@requires_search_service
@pytest.mark.options(ELASTICSEARCH_URL="http://localhost:9200", AUTO_INDEX=True)
class SearchIntegrationTest(APITestCase):
    """Integration tests that require a running search-service and Elasticsearch."""

    @pytest.fixture(autouse=True)
    def clean_es(self, app):
        from udata.search import get_elastic_client

        es_client = get_elastic_client()
        es_client.es.indices.delete(index="udata-test-*", ignore=[404])
        es_client.init_indices()
        yield

    def test_dataset_fuzzy_search(self):
        """
        Test that Elasticsearch fuzzy search works.

        A typo in the search query ("spectakulaire" instead of "spectaculaire")
        should still find the dataset thanks to ES fuzzy matching.
        """
        DatasetFactory(title="Données spectaculaires sur les transports")

        # Small delay to let ES index the document
        time.sleep(1)

        # Search with a typo - only ES fuzzy search can handle this
        response = self.get("/api/2/datasets/search/?q=spectakulaire")
        self.assert200(response)
        assert response.json["total"] >= 1

        titles = [d["title"] for d in response.json["data"]]
        assert "Données spectaculaires sur les transports" in titles

    def test_dataset_filter_by_format_family(self):
        """Test filtering datasets by format_family."""
        csv_resource = ResourceFactory(format="csv")
        json_resource = ResourceFactory(format="json")
        DatasetFactory(title="Dataset tabular", resources=[csv_resource])
        DatasetFactory(title="Dataset machine readable", resources=[json_resource])

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?format_family=tabular")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset tabular" in titles
        assert "Dataset machine readable" not in titles

    def test_dataset_filter_by_producer_type(self):
        """Test filtering datasets by producer_type."""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        user = UserFactory()

        DatasetFactory(title="Dataset public service", organization=org)
        DatasetFactory(title="Dataset user", owner=user, organization=None)

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?producer_type=public-service")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset public service" in titles
        assert "Dataset user" not in titles

    def test_dataset_facets_counts(self):
        """Test that facets return correct counts, including the 'all' total."""
        license_cc = LicenseFactory(id="cc-by")
        license_odbl = LicenseFactory(id="odc-odbl")
        DatasetFactory(title="DS1", license=license_cc, tags=["transport"])
        DatasetFactory(title="DS2", license=license_cc, tags=["sante"])
        DatasetFactory(title="DS3", license=license_odbl, tags=["transport"])

        time.sleep(1)

        # Without filter: all 3 datasets, facets show totals
        response = self.get("/api/2/datasets/search/")
        self.assert200(response)
        assert response.json["total"] == 3
        facets = response.json["facets"]
        license_facet = facets["license"]
        license_all = next(f for f in license_facet if f["name"] == "all")
        assert license_all["count"] == 3
        license_cc_bucket = next(f for f in license_facet if f["name"] == "cc-by")
        assert license_cc_bucket["count"] == 2
        license_odbl_bucket = next(f for f in license_facet if f["name"] == "odc-odbl")
        assert license_odbl_bucket["count"] == 1

        # With a tag filter: facet "all" for license should still be 2
        # (docs matching tag=transport, regardless of license)
        response = self.get("/api/2/datasets/search/?tag=transport")
        self.assert200(response)
        assert response.json["total"] == 2
        facets = response.json["facets"]
        license_facet = facets["license"]
        license_all = next(f for f in license_facet if f["name"] == "all")
        assert license_all["count"] == 2

    def test_reuse_search(self):
        """Test reuse search endpoint."""
        VisibleReuseFactory(title="Réutilisation de données ouvertes")

        time.sleep(1)

        response = self.get("/api/2/reuses/search/?q=ouvertes")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [r["title"] for r in response.json["data"]]
        assert "Réutilisation de données ouvertes" in titles

    def test_reuse_filter_by_producer_type(self):
        """Test filtering reuses by producer_type."""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        user = UserFactory()

        VisibleReuseFactory(title="Reuse public service", organization=org)
        VisibleReuseFactory(title="Reuse by user", owner=user, organization=None)

        time.sleep(1)

        response = self.get("/api/2/reuses/search/?producer_type=public-service")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [r["title"] for r in response.json["data"]]
        assert "Reuse public service" in titles
        assert "Reuse by user" not in titles

        response = self.get("/api/2/reuses/search/?producer_type=user")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [r["title"] for r in response.json["data"]]
        assert "Reuse by user" in titles
        assert "Reuse public service" not in titles

    def test_dataservice_search(self):
        """Test dataservice search endpoint."""
        dataservice = DataserviceFactory(title="API des transports en commun")

        time.sleep(1)

        response = self.get("/api/2/dataservices/search/?q=transports")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "API des transports en commun" in titles

        # TODO: Temporary workaround until udata-search-service is migrated into udata.
        # drop_database doesn't trigger MongoEngine signals, so we need to manually delete
        # to trigger unindex and avoid polluting ES for subsequent tests.
        # There's no HTTP endpoint to trigger clean-es remotely on the search service.
        dataservice.delete()
        time.sleep(1)

        response = self.get("/api/2/dataservices/search/?q=transports")
        self.assert200(response)
        assert response.json["total"] == 0

    def test_organization_search(self):
        """Test organization search endpoint."""
        OrganizationFactory(name="Direction du numérique")

        time.sleep(1)

        response = self.get("/api/2/organizations/search/?q=numérique")
        self.assert200(response)
        assert response.json["total"] >= 1
        names = [o["name"] for o in response.json["data"]]
        assert "Direction du numérique" in names

    def test_topic_search(self):
        """Test topic search endpoint."""
        TopicFactory(name="Transports et mobilité", private=False)

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=mobilité")
        self.assert200(response)
        assert response.json["total"] >= 1
        names = [t["name"] for t in response.json["data"]]
        assert "Transports et mobilité" in names

    def test_topic_sort_by_name(self):
        TopicFactory(name="aaa topic", private=False)
        TopicFactory(name="zzz topic", private=False)

        time.sleep(1)

        response = self.get("/api/2/topics/search/?sort=name")
        self.assert200(response)
        assert response.json["total"] == 2
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "aaa topic"
        assert names[1] == "zzz topic"

        response = self.get("/api/2/topics/search/?sort=-name")
        self.assert200(response)
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "zzz topic"
        assert names[1] == "aaa topic"

    def test_topic_sort_by_created(self):
        from datetime import datetime

        TopicFactory(name="old topic", private=False, created_at=datetime(2020, 1, 1))
        TopicFactory(name="new topic", private=False, created_at=datetime(2024, 1, 1))

        time.sleep(1)

        response = self.get("/api/2/topics/search/?sort=created")
        self.assert200(response)
        assert response.json["total"] == 2
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "old topic"
        assert names[1] == "new topic"

        response = self.get("/api/2/topics/search/?sort=-created")
        self.assert200(response)
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "new topic"
        assert names[1] == "old topic"

    def test_topic_sort_by_last_modified(self):
        import time as time_mod

        TopicFactory(name="old topic", private=False)
        time_mod.sleep(1.5)
        TopicFactory(name="new topic", private=False)

        time.sleep(1)

        response = self.get("/api/2/topics/search/?sort=last_modified")
        self.assert200(response)
        assert response.json["total"] == 2
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "old topic"
        assert names[1] == "new topic"

        response = self.get("/api/2/topics/search/?sort=-last_modified")
        self.assert200(response)
        names = [t["name"] for t in response.json["data"]]
        assert names[0] == "new topic"
        assert names[1] == "old topic"

    def test_topic_search_by_element_title(self):
        """A topic should be findable by its elements' titles in ES."""
        topic = TopicFactory(name="unrelated topic name", description="unrelated description")
        TopicElementFactory(
            topic=topic, title="climate change data", description="some description"
        )
        TopicFactory(name="other topic", description="other description")

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=climate")
        self.assert200(response)
        ids = [t["id"] for t in response.json["data"]]
        assert str(topic.id) in ids
        assert response.json["total"] == 1

    def test_topic_search_by_element_description(self):
        """A topic should be findable by its elements' descriptions in ES."""
        topic = TopicFactory(name="unrelated topic name", description="unrelated description")
        TopicElementFactory(
            topic=topic, title="some title", description="environmental datasets about biodiversity"
        )
        TopicFactory(name="other topic", description="other description")

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=biodiversity")
        self.assert200(response)
        ids = [t["id"] for t in response.json["data"]]
        assert str(topic.id) in ids
        assert response.json["total"] == 1

    def test_topic_search_by_element_tag(self):
        """A topic should be findable by its elements' tags in ES."""
        topic = TopicFactory(name="unrelated topic name", description="unrelated description")
        TopicElementFactory(topic=topic, title="some title", tags=["renewable-energy"])
        TopicFactory(name="other topic", description="other description")

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=renewable-energy")
        self.assert200(response)
        ids = [t["id"] for t in response.json["data"]]
        assert str(topic.id) in ids
        assert response.json["total"] == 1

    def test_topic_search_element_deleted(self):
        """Deleting an element should remove its content from the topic's index."""
        topic = TopicFactory(name="unrelated topic name", description="unrelated description")
        elem = TopicElementFactory(
            topic=topic, title="climate change data", tags=["renewable-energy"]
        )
        TopicFactory(name="other topic", description="other description")

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=climate")
        self.assert200(response)
        assert response.json["total"] == 1

        elem.delete()
        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=climate")
        self.assert200(response)
        assert response.json["total"] == 0

        response = self.get("/api/2/topics/search/?q=renewable-energy")
        self.assert200(response)
        assert response.json["total"] == 0

    def test_topic_search_element_updated(self):
        """Updating an element should reflect new content in the topic's index."""
        topic = TopicFactory(name="unrelated topic name", description="unrelated description")
        elem = TopicElementFactory(
            topic=topic, title="climate change data", tags=["renewable-energy"]
        )
        TopicFactory(name="other topic", description="other description")

        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=climate")
        self.assert200(response)
        assert response.json["total"] == 1

        elem.title = "ocean biodiversity data"
        elem.tags = ["marine"]
        elem.save()
        time.sleep(1)

        response = self.get("/api/2/topics/search/?q=climate")
        self.assert200(response)
        assert response.json["total"] == 0

        response = self.get("/api/2/topics/search/?q=biodiversity")
        self.assert200(response)
        assert response.json["total"] == 1

    def test_discussion_search(self):
        """Test discussion search endpoint."""
        dataset = DatasetFactory()
        user = UserFactory()
        DiscussionFactory(title="Question sur les données", subject=dataset, user=user)

        time.sleep(1)

        response = self.get("/api/2/discussions/search/?q=données")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Question sur les données" in titles

    def test_post_search(self):
        """Test post search endpoint."""
        PostFactory(name="Actualités open data", headline="Les dernières nouvelles")

        time.sleep(1)

        response = self.get("/api/2/posts/search/?q=actualités")
        self.assert200(response)
        assert response.json["total"] >= 1
        names = [p["name"] for p in response.json["data"]]
        assert "Actualités open data" in names

    def test_dataset_filter_by_multiple_tags(self):
        """Test filtering datasets by multiple tags."""
        DatasetFactory(title="Dataset with both tags", tags=["transport", "environnement"])
        DatasetFactory(title="Dataset transport only", tags=["transport"])
        DatasetFactory(title="Dataset environnement only", tags=["environnement"])

        time.sleep(1)

        # Filter by both tags - should only return dataset with both
        response = self.get("/api/2/datasets/search/?tag=transport&tag=environnement")
        self.assert200(response)
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset with both tags" in titles

    def test_organization_filter_by_producer_type(self):
        """Test filtering organizations by producer_type."""
        org_ps = OrganizationFactory(name="Org service public")
        org_ps.add_badge(PUBLIC_SERVICE)
        org_ps.save()

        org_company = OrganizationFactory(name="Org entreprise")
        org_company.add_badge(COMPANY)
        org_company.save()

        time.sleep(2)

        response = self.get("/api/2/organizations/search/?producer_type=public-service")
        self.assert200(response)
        assert response.json["total"] >= 1
        ids = [o["id"] for o in response.json["data"]]
        assert str(org_ps.id) in ids
        assert str(org_company.id) not in ids

    def test_organization_search_with_badge_filter(self):
        """Test that organization search with badge filter returns matching organizations."""
        org = OrganizationFactory()
        org.add_badge(org_constants.PUBLIC_SERVICE)
        org.save()

        time.sleep(2)

        response = self.get("/api/2/organizations/search/?badge=public-service")
        self.assert200(response)
        assert response.json["total"] >= 1
        ids = [o["id"] for o in response.json["data"]]
        assert str(org.id) in ids

    def test_reuse_search_with_organization_filter(self):
        """
        Regression test for: 500 Server Error when None values are passed to search service.

        When searching reuses with only an organization filter, other params should not be
        sent as literal 'None' strings (e.g. ?q=None&tag=None).
        """
        org = OrganizationFactory()
        reuse = VisibleReuseFactory(organization=org)

        time.sleep(1)

        response = self.get(f"/api/2/reuses/search/?organization={org.id}")
        self.assert200(response)
        assert response.json["total"] >= 1
        ids = [r["id"] for r in response.json["data"]]
        assert str(reuse.id) in ids

    def test_organization_search_with_query(self):
        """
        Regression test for: 500 Server Error when None values are passed to search service.

        When searching organizations, other params should not be sent as literal
        'None' strings (e.g. ?badge=None).
        """
        org = OrganizationFactory(name="Organisation Unique Test")

        time.sleep(1)

        response = self.get("/api/2/organizations/search/?q=unique")
        self.assert200(response)
        assert response.json["total"] >= 1
        ids = [o["id"] for o in response.json["data"]]
        assert str(org.id) in ids

    def test_dataservice_search_with_is_restricted_filter(self):
        """
        Regression test for is_restricted filter when passed to search service.
        """
        restricted_dataservice = DataserviceFactory(access_type=AccessType.RESTRICTED)
        open_dataservice = DataserviceFactory(access_type=AccessType.OPEN)
        open_with_account_dataservice = DataserviceFactory(access_type=AccessType.OPEN_WITH_ACCOUNT)

        time.sleep(1)

        response = self.get("/api/2/dataservices/search/")
        self.assert200(response)
        assert response.json["total"] == 3

        response = self.get("/api/2/dataservices/search/?is_restricted=true")
        self.assert200(response)
        assert response.json["total"] == 1
        ids = [o["id"] for o in response.json["data"]]
        assert set([str(restricted_dataservice.id)]) == set(ids)

        response = self.get("/api/2/dataservices/search/?is_restricted=false")
        self.assert200(response)
        assert response.json["total"] == 2
        ids = [o["id"] for o in response.json["data"]]
        assert set([str(open_dataservice.id), str(open_with_account_dataservice.id)]) == set(ids)

    def test_dataset_sort_by_created(self):
        from datetime import datetime

        DatasetFactory(title="Ancien", created_at_internal=datetime(2020, 1, 1))
        DatasetFactory(title="Récent", created_at_internal=datetime(2024, 1, 1))

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?sort=-created")
        self.assert200(response)
        assert response.json["total"] == 2
        titles = [d["title"] for d in response.json["data"]]
        assert titles[0] == "Récent"

    def test_dataset_filter_by_license(self):
        license_cc = LicenseFactory(id="cc-by")
        license_odbl = LicenseFactory(id="odc-odbl")
        DatasetFactory(title="CC-BY", license=license_cc)
        DatasetFactory(title="ODbL", license=license_odbl)

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?license=cc-by")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "CC-BY" in titles
        assert "ODbL" not in titles

    def test_dataset_filter_by_organization(self):
        org = OrganizationFactory()
        DatasetFactory(title="Dataset org", organization=org)
        DatasetFactory(title="Dataset autre")

        time.sleep(1)

        response = self.get(f"/api/2/datasets/search/?organization={org.id}")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset org" in titles
        assert "Dataset autre" not in titles

    def test_dataset_filter_by_owner(self):
        user = UserFactory()
        DatasetFactory(title="Dataset user", owner=user, organization=None)
        DatasetFactory(title="Dataset autre")

        time.sleep(1)

        response = self.get(f"/api/2/datasets/search/?owner={user.id}")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset user" in titles
        assert "Dataset autre" not in titles

    def test_dataset_filter_by_schema(self):
        from udata.core.dataset.models import Schema

        resource_with_schema = ResourceFactory(schema=Schema(name="etalab/schema-irve"))
        DatasetFactory(title="Avec schéma", resources=[resource_with_schema])
        DatasetFactory(title="Sans schéma")

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?schema=etalab/schema-irve")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Avec schéma" in titles

    def test_dataset_filter_by_badge(self):
        from udata.core.constants import HVD

        ds = DatasetFactory(title="Dataset avec badge")
        ds.add_badge(HVD)

        DatasetFactory(title="Dataset sans badge")

        time.sleep(1)

        response = self.get(f"/api/2/datasets/search/?badge={HVD}")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "Dataset avec badge" in titles

    def test_dataset_pagination(self):
        for i in range(4):
            DatasetFactory(title=f"Dataset {i}")

        time.sleep(1)

        response = self.get("/api/2/datasets/search/?page_size=2&page=1")
        self.assert200(response)
        assert len(response.json["data"]) == 2
        assert response.json["page"] == 1
        assert response.json["page_size"] == 2
        assert response.json["total"] == 4
        assert response.json["next_page"] is not None
        assert response.json["previous_page"] is None

        response = self.get("/api/2/datasets/search/?page_size=2&page=2")
        self.assert200(response)
        assert len(response.json["data"]) == 2
        assert response.json["page"] == 2
        assert response.json["previous_page"] is not None

    def test_reuse_filter_by_type(self):
        VisibleReuseFactory(title="API reuse", type="api")
        VisibleReuseFactory(title="App reuse", type="application")

        time.sleep(1)

        response = self.get("/api/2/reuses/search/?type=api")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [r["title"] for r in response.json["data"]]
        assert "API reuse" in titles
        assert "App reuse" not in titles

    def test_reuse_filter_by_owner(self):
        user = UserFactory()
        VisibleReuseFactory(title="Reuse user", owner=user, organization=None)
        VisibleReuseFactory(title="Reuse autre")

        time.sleep(1)

        response = self.get(f"/api/2/reuses/search/?owner={user.id}")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [r["title"] for r in response.json["data"]]
        assert "Reuse user" in titles
        assert "Reuse autre" not in titles

    def test_dataservice_filter_by_organization(self):
        org = OrganizationFactory()
        DataserviceFactory(title="DS org", organization=org)
        DataserviceFactory(title="DS autre")

        time.sleep(1)

        response = self.get(f"/api/2/dataservices/search/?organization={org.id}")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "DS org" in titles
        assert "DS autre" not in titles

    def test_dataservice_filter_by_tags(self):
        DataserviceFactory(title="DS tagged", tags=["transport"])
        DataserviceFactory(title="DS other", tags=["sante"])

        time.sleep(1)

        response = self.get("/api/2/dataservices/search/?tag=transport")
        self.assert200(response)
        assert response.json["total"] >= 1
        titles = [d["title"] for d in response.json["data"]]
        assert "DS tagged" in titles
        assert "DS other" not in titles

    def test_suggest_organizations_with_dataset_count(self):
        """count_for=dataset annotates each suggestion and pushes empty orgs to the end."""
        org_two = OrganizationFactory(name="Count Alpha")
        org_one = OrganizationFactory(name="Count Beta")
        OrganizationFactory(name="Count Empty")
        DatasetFactory(organization=org_two)
        DatasetFactory(organization=org_two)
        DatasetFactory(organization=org_one)

        time.sleep(1)

        response = self.get(
            url_for("api.suggest_organizations", q="Count", size=10, count_for="dataset")
        )
        self.assert200(response)
        counts = {org["name"]: org["matching_count"] for org in response.json}
        assert counts == {"Count Alpha": 2, "Count Beta": 1, "Count Empty": 0}
        # The empty organization is demoted to the end, the others keep their ranking.
        assert response.json[-1]["name"] == "Count Empty"

    def test_suggest_organizations_count_scoped_by_filter(self):
        """The count respects the count_filter.* search context."""
        org = OrganizationFactory(name="Scoped Org")
        DatasetFactory(organization=org, tags=["transport"])
        DatasetFactory(organization=org, tags=["sante"])

        time.sleep(1)

        response = self.get(
            url_for(
                "api.suggest_organizations",
                q="Scoped",
                size=10,
                count_for="dataset",
                **{"count_filter.tag": "transport"},
            )
        )
        self.assert200(response)
        assert response.json[0]["name"] == "Scoped Org"
        assert response.json[0]["matching_count"] == 1

    def test_suggest_organizations_dataservice_count(self):
        """count_for=dataservice replaces the old "orgs with at least one API" flag."""
        org_api = OrganizationFactory(name="Api Provider")
        OrganizationFactory(name="Api Nothing")
        DataserviceFactory(organization=org_api)

        time.sleep(1)

        response = self.get(
            url_for("api.suggest_organizations", q="Api", size=10, count_for="dataservice")
        )
        self.assert200(response)
        counts = {org["name"]: org["matching_count"] for org in response.json}
        assert counts == {"Api Provider": 1, "Api Nothing": 0}
        assert response.json[-1]["name"] == "Api Nothing"

    def test_suggest_organizations_restricted_by_topic(self):
        """`topic` restricts candidates to orgs owning a dataset in the topic."""
        in_topic = OrganizationFactory(name="Topic Member")
        out_topic = OrganizationFactory(name="Topic Outsider")
        dataset_in = DatasetFactory(organization=in_topic)
        DatasetFactory(organization=out_topic)
        topic = TopicFactory()
        TopicElementDatasetFactory(topic=topic, element=dataset_in)

        time.sleep(1)

        response = self.get(
            url_for(
                "api.suggest_organizations",
                q="Topic",
                size=10,
                count_for="dataset",
                topic=str(topic.id),
            )
        )
        self.assert200(response)
        names = [org["name"] for org in response.json]
        assert names == ["Topic Member"]
        assert response.json[0]["matching_count"] == 1

    def test_suggest_organizations_facet_ids_surface_relevant_orgs(self):
        """count_facet_ids brings in result-having orgs beyond the follower-limited top."""
        org_top = OrganizationFactory(name="Facet One", metrics={"followers": 3})
        OrganizationFactory(name="Facet Two", metrics={"followers": 2})  # no dataset
        org_low = OrganizationFactory(name="Facet Three", metrics={"followers": 1})
        DatasetFactory(organization=org_top)
        DatasetFactory(organization=org_low)

        time.sleep(1)

        # size=2 → A (top followers) = One, Two ; Three is only reachable via the facet ids.
        response = self.get(
            url_for(
                "api.suggest_organizations",
                q="Facet",
                size=2,
                count_for="dataset",
                count_facet_ids=str(org_low.id),
            )
        )
        self.assert200(response)
        # "Two" (0 result) is demoted out, "Three" surfaces thanks to the facet ids.
        assert [org["name"] for org in response.json] == ["Facet One", "Facet Three"]
        assert [org["matching_count"] for org in response.json] == [1, 1]

    def test_suggest_organizations_reuse_count(self):
        """count_for=reuse counts reuses per organization."""
        org = OrganizationFactory(name="Reuse Org")
        VisibleReuseFactory(organization=org)
        VisibleReuseFactory(organization=org)

        time.sleep(1)

        response = self.get(
            url_for("api.suggest_organizations", q="Reuse", size=10, count_for="reuse")
        )
        self.assert200(response)
        assert response.json[0]["name"] == "Reuse Org"
        assert response.json[0]["matching_count"] == 2

    def test_suggest_organizations_ranked_by_followers_not_count(self):
        """Among orgs with results, ranking is by followers — never by number of matches."""
        popular = OrganizationFactory(name="Rank Popular", metrics={"followers": 100})
        prolific = OrganizationFactory(name="Rank Prolific", metrics={"followers": 1})
        DatasetFactory(organization=popular)
        DatasetFactory.create_batch(3, organization=prolific)

        time.sleep(1)

        response = self.get(
            url_for("api.suggest_organizations", q="Rank", size=10, count_for="dataset")
        )
        self.assert200(response)
        # Prolific has more datasets, but Popular has far more followers → Popular first.
        assert [org["name"] for org in response.json] == ["Rank Popular", "Rank Prolific"]
        assert {org["name"]: org["matching_count"] for org in response.json} == {
            "Rank Popular": 1,
            "Rank Prolific": 3,
        }

    def test_suggest_organizations_topic_restriction_and_count_are_independent(self):
        """`topic` restricts candidates; the count scope is driven separately by count_filter."""
        org = OrganizationFactory(name="Deco Org")
        dataset_in = DatasetFactory(organization=org)
        DatasetFactory(organization=org)  # second dataset, not in the topic
        topic = TopicFactory()
        TopicElementDatasetFactory(topic=topic, element=dataset_in)

        time.sleep(1)

        # Restricted to the topic universe, no count scope → counts all org datasets (2).
        response = self.get(
            url_for(
                "api.suggest_organizations",
                q="Deco",
                size=10,
                count_for="dataset",
                topic=str(topic.id),
            )
        )
        self.assert200(response)
        assert response.json[0]["matching_count"] == 2

        # Same candidates, but the count is scoped to the topic via count_filter → 1.
        response = self.get(
            url_for(
                "api.suggest_organizations",
                q="Deco",
                size=10,
                count_for="dataset",
                topic=str(topic.id),
                **{"count_filter.topic": str(topic.id)},
            )
        )
        self.assert200(response)
        assert response.json[0]["matching_count"] == 1
