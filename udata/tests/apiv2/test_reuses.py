from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.user.factories import UserFactory
from udata.search.query import ES_MAX_RESULT_WINDOW
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert400


class ReuseSearchAPIV2Test(APITestCase):
    def test_reuse_search_with_model_query_param(self):
        ReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        assert200(response)

    def test_search_returns_400_when_pagination_exceeds_es_max_result_window(self):
        response = self.get("/api/2/reuses/search/?page=8925&page_size=20")
        assert400(response)
        max_page = ES_MAX_RESULT_WINDOW // 20
        assert f"Maximum page for this page_size is {max_page}" in response.json["message"]


class ReuseListAPIV2Test(APITestCase):
    def test_reuse_list(self):
        """The reuse list exposes datasets as a subsection link, not the full list."""
        reuse = VisibleReuseFactory(datasets=DatasetFactory.create_batch(3))

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 1

        data = response.json["data"][0]
        assert data["id"] == str(reuse.id)
        assert data["datasets"]["rel"] == "subsection"
        assert data["datasets"]["type"] == "GET"
        assert data["datasets"]["total"] == 3
        # The link points to the datasets listing endpoint filtered on this reuse.
        assert str(reuse.id) in data["datasets"]["href"]

    def test_reuse_list_pagination(self):
        ReuseFactory.create_batch(10)

        response = self.get(url_for("apiv2.reuses", page=2, page_size=3))
        assert200(response)
        assert len(response.json["data"]) == 3
        assert response.json["page"] == 2
        assert response.json["page_size"] == 3
        assert response.json["total"] == 10

    def test_reuse_list_filter_private(self):
        user = UserFactory()
        public_reuse = ReuseFactory()
        private_reuse = ReuseFactory(private=True, owner=user)

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(public_reuse.id)}

        self.login(user)
        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(public_reuse.id), str(private_reuse.id)}
