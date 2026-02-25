import time

import pytest

from udata.core.access_type.constants import AccessType
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
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
@pytest.mark.options(SEARCH_SERVICE_API_URL="http://localhost:5000/api/1/", AUTO_INDEX=True)
class SearchIntegrationTest(APITestCase):
    """Integration tests that require a running search-service and Elasticsearch."""

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
