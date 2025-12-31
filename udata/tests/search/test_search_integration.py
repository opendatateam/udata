import time

import pytest

from udata.core.dataset.factories import DatasetFactory
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
