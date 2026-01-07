import time

import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.core.organization import constants as org_constants
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import VisibleReuseFactory
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

    def test_organization_search_with_badge_filter(self):
        """
        Regression test for: 500 Server Error when None values are passed to search service.

        When searching organizations with only a badge filter, other params should not be
        sent as literal 'None' strings (e.g. ?q=None&tag=None).
        """
        org = OrganizationFactory()
        org.add_badge(org_constants.PUBLIC_SERVICE)
        org.save()

        time.sleep(1)

        response = self.get("/api/2/organizations/search/?badge=public-service")
        self.assert200(response)
        assert response.json["total"] >= 1
        ids = [o["id"] for o in response.json["data"]]
        assert str(org.id) in ids
