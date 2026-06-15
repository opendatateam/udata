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

    def test_reuse_list_datasets_link_filters_to_reuse(self):
        """Following the `datasets.href` returns exactly the reuse datasets.
        Asserting the id appears in the URL is not enough: a regression on the
        filter param name would keep the id in the query string yet break the
        link. This follows the link end-to-end to guard the wiring."""
        reuse_datasets = DatasetFactory.create_batch(2)
        VisibleReuseFactory(datasets=reuse_datasets)
        other_dataset = DatasetFactory()  # not linked to the reuse

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        href = response.json["data"][0]["datasets"]["href"]

        datasets_response = self.get(href)
        assert200(datasets_response)
        returned_ids = {d["id"] for d in datasets_response.json["data"]}
        assert returned_ids == {str(d.id) for d in reuse_datasets}
        assert str(other_dataset.id) not in returned_ids

    def test_reuse_list_datasets_link_when_empty(self):
        """A reuse without datasets still exposes a valid subsection link with a
        `total` of 0 (the `metrics.get("datasets", 0)` default branch)."""
        VisibleReuseFactory(datasets=[])

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        data = response.json["data"][0]
        assert data["datasets"]["rel"] == "subsection"
        assert data["datasets"]["total"] == 0
        assert data["datasets"]["href"]

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

    def test_reuse_list_private_isolation_between_users(self):
        """A private reuse is only visible to its owner, never to another logged-in
        user. Guards the `| owned_qs` branch of `visible_by_user`: a regression
        broadening it would still pass `test_reuse_list_filter_private`."""
        owner = UserFactory()
        other_user = UserFactory()
        public_reuse = ReuseFactory()
        ReuseFactory(private=True, owner=owner)

        self.login(other_user)
        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(public_reuse.id)}

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

    def test_reuse_list_filter_dataset(self):
        """The `dataset` filter (key of the `datasets` field) narrows the listing
        to the reuses linked to a given dataset — the core relation of this API."""
        dataset = DatasetFactory()
        linked_reuse = VisibleReuseFactory(datasets=[dataset])
        VisibleReuseFactory(datasets=DatasetFactory.create_batch(1))

        response = self.get(url_for("apiv2.reuses", dataset=str(dataset.id)))
        assert200(response)
        ids = {r["id"] for r in response.json["data"]}
        assert ids == {str(linked_reuse.id)}

    def test_reuse_list_exposes_owner(self):
        """The `owner` reference is dereferenced and serialized under
        `no_dereference()`, symmetrically to `organization`."""
        user = UserFactory()
        VisibleReuseFactory(owner=user, organization=None, datasets=DatasetFactory.create_batch(1))

        response = self.get(url_for("apiv2.reuses"))
        assert200(response)
        assert response.json["data"][0]["owner"]["id"] == str(user.id)
