import time

import pytest

from udata.core.access_type.constants import AccessType
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization import constants as org_constants
from udata.core.organization.constants import COMPANY, PUBLIC_SERVICE
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import TopicFactory
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
