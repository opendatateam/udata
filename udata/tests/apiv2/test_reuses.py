from udata.core.reuse.factories import ReuseFactory
from udata.tests.api import APITestCase


class ReuseSearchAPIV2Test(APITestCase):
    def test_reuse_search_with_model_query_param(self):
        """Searching reuses with 'model' as query param should not crash."""
        ReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        self.assert200(response)
