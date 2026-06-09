from datetime import datetime

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.user.factories import UserFactory
from udata.models import Reuse
from udata.search.query import ES_MAX_RESULT_WINDOW
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert400


class ReuseSearchAPIV2Test(APITestCase):
    def test_reuse_search_with_model_query_param(self):
        ReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        assert200(response)

    def test_reuse_search_datasets_total_from_counter(self):
        """`datasets.total` comes from the stored metric, so searching reuses
        never dereferences the (potentially heavy) linked datasets."""
        reuse = VisibleReuseFactory(datasets=DatasetFactory.create_batch(2))
        # Desync the stored counter from the real number of datasets: a `total`
        # read from the counter proves we don't dereference (which would yield 2).
        Reuse.objects(id=reuse.id).update(set__metrics__datasets=99)

        response = self.get(url_for("apiv2.reuse_search"))
        assert200(response)
        data = response.json["data"][0]
        assert data["datasets"]["rel"] == "subsection"
        assert data["datasets"]["total"] == 99
        assert str(reuse.id) in data["datasets"]["href"]

    def test_search_returns_400_when_pagination_exceeds_es_max_result_window(self):
        response = self.get("/api/2/reuses/search/?page=8925&page_size=20")
        assert400(response)
        max_page = ES_MAX_RESULT_WINDOW // 20
        assert f"Maximum page for this page_size is {max_page}" in response.json["message"]


class ReuseListAPIV2Test(APITestCase):
    def test_reuse_list(self):
        """The reuse list exposes datasets as a subsection link, not the full list."""
        reuse = VisibleReuseFactory(datasets=DatasetFactory.create_batch(3))
        # In prod the `datasets` metric is kept up to date by on_create/on_update
        # signals; those are muted in factories, so refresh it explicitly here.
        reuse.count_datasets()

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

    def test_reuse_list_datasets_total_from_counter(self):
        """`datasets.total` comes from the stored metric, not from dereferencing
        and counting the linked datasets."""
        reuse = VisibleReuseFactory(datasets=DatasetFactory.create_batch(2))
        Reuse.objects(id=reuse.id).update(set__metrics__datasets=99)

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        assert response.json["data"][0]["datasets"]["total"] == 99

    def test_reuse_list_exposes_organization(self):
        """References other than `datasets` (e.g. organization) are still
        dereferenced and serialized."""
        org = OrganizationFactory()
        VisibleReuseFactory(organization=org, datasets=DatasetFactory.create_batch(1))

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        assert response.json["data"][0]["organization"]["id"] == str(org.id)

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

    def test_reuse_list_excludes_deleted(self):
        """Deleted reuses are filtered out by the endpoint `deleted=None` clause;
        `deleted` is not `filterable`, so only this test guards that exclusion."""
        public_reuse = ReuseFactory()
        ReuseFactory(deleted=datetime.utcnow())

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(public_reuse.id)}

    def test_reuse_list_sort_by_datasets(self):
        """`?sort=-datasets` orders on the stored `metrics.datasets` counter."""
        most, mid, least = ReuseFactory.create_batch(3)
        Reuse.objects(id=most.id).update(set__metrics__datasets=10)
        Reuse.objects(id=mid.id).update(set__metrics__datasets=5)
        Reuse.objects(id=least.id).update(set__metrics__datasets=1)

        response = self.get(url_for("apiv2.reuses", sort="-datasets"))
        assert200(response)
        ids = [r["id"] for r in response.json["data"]]
        assert ids == [str(most.id), str(mid.id), str(least.id)]

    def test_reuse_list_filter_type(self):
        """The `type` filter exposed by `__index_parser__` narrows the listing."""
        api_reuse = ReuseFactory(type="api")
        ReuseFactory(type="application")

        response = self.get(url_for("apiv2.reuses", type="api"))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(api_reuse.id)}
