from flask import g, url_for
from mongoengine.context_managers import query_counter

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    DataserviceBloc,
    DatasetBloc,
    ReuseBloc,
    SectionBloc,
    TitleBloc,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.models import Site
from udata.core.user.factories import AdminFactory
from udata.tests.api import APITestCase


class SiteAPITest(APITestCase):
    def test_get_site(self):
        response = self.get(url_for("api.site"))
        self.assert200(response)

        site = Site.objects.get(id=self.app.config["SITE_ID"])

        self.assertEqual(site.title, response.json["title"])

    def test_get_site_hides_blocs_by_default(self):
        response = self.get(url_for("api.site"))
        self.assert200(response)
        assert "datasets_blocs" not in response.json
        assert "reuses_blocs" not in response.json
        assert "dataservices_blocs" not in response.json

    def _set_site_blocs(self, datasets_blocs=None, reuses_blocs=None, dataservices_blocs=None):
        # Trigger site creation via the API, then attach blocs and reset the cache in
        # flask.g so the site is reloaded from DB.
        self.get(url_for("api.site"))
        site = Site.objects.get(id=self.app.config["SITE_ID"])
        site.datasets_blocs = datasets_blocs or []
        site.reuses_blocs = reuses_blocs or []
        site.dataservices_blocs = dataservices_blocs or []
        site.save()
        g.site = None

    def test_get_site_with_x_fields_shows_blocs(self):
        self._set_site_blocs(
            datasets_blocs=[SectionBloc(color="green", blocs=[TitleBloc(title="Test")])]
        )

        response = self.get(url_for("api.site"), headers={"X-Fields": "{*}"})
        self.assert200(response)
        assert "datasets_blocs" in response.json
        (section,) = response.json["datasets_blocs"]
        assert (section["class"], section["color"]) == ("SectionBloc", "green")

    def test_get_site_does_not_prefetch_masked_blocs(self):
        """Blocs are masked out of the default `/site/` response, so their references
        must not be prefetched — that would add latency for data nobody requested."""
        org = OrganizationFactory()

        def query_count(nb_cards):
            # Fill all three bloc fields: without the mask guard, every one would be
            # prefetched (a batch query per type), adding several useless queries.
            def sections(blocs):
                return [SectionBloc(blocs=blocs)] if blocs else []

            self._set_site_blocs(
                datasets_blocs=sections(
                    [DatasetBloc(dataset=DatasetFactory(organization=org)) for _ in range(nb_cards)]
                ),
                reuses_blocs=sections(
                    [ReuseBloc(reuse=ReuseFactory(organization=org)) for _ in range(nb_cards)]
                ),
                dataservices_blocs=sections(
                    [
                        DataserviceBloc(dataservice=DataserviceFactory(organization=org))
                        for _ in range(nb_cards)
                    ]
                ),
            )

            self.assert200(self.get(url_for("api.site")))  # warm up one-time queries
            g.site = None

            with query_counter() as counter:
                response = self.get(url_for("api.site"))
                count = int(counter)
            self.assert200(response)
            assert "datasets_blocs" not in response.json
            return count

        # Compared against no blocs, not fewer cards: a prefetch that ignores the mask
        # costs a constant batch query per type, which a "20 vs 2 cards" comparison would
        # not see. Without blocs, there is nothing to load, so it gives the baseline count.
        filled, empty = query_count(20), query_count(0)
        assert filled == empty, (
            f"the query count grows with the bloc contents ({filled} with cards, "
            f"{empty} without): the masked-out blocs are prefetched"
        )

    def test_get_site_blocs_no_n_plus_1(self):
        """When blocs are requested (X-Fields), their references must be batched."""
        orgs = OrganizationFactory.create_batch(2)
        headers = {"X-Fields": "{*}"}

        def query_count(nb_cards):
            datasets = [DatasetFactory(organization=orgs[i % len(orgs)]) for i in range(nb_cards)]
            self._set_site_blocs(
                datasets_blocs=[SectionBloc(blocs=[DatasetBloc(dataset=d) for d in datasets])]
            )

            self.assert200(self.get(url_for("api.site"), headers=headers))  # warm up
            g.site = None

            with query_counter() as counter:
                response = self.get(url_for("api.site"), headers=headers)
                count = int(counter)
            self.assert200(response)
            blocs = response.json["datasets_blocs"][0]["blocs"]
            assert [bloc["dataset"]["id"] for bloc in blocs] == [str(d.id) for d in datasets]
            return count

        many, few = query_count(20), query_count(2)
        assert many == few, (
            f"the query count grows with the number of cards ({many} for 20 cards, "
            f"{few} for 2): the references are dereferenced one by one"
        )

    def test_set_site_blocs(self):
        dataset = DatasetFactory()
        self.login(AdminFactory())
        response = self.patch(
            url_for("api.site"),
            {
                "datasets_blocs": [
                    {
                        "class": "SectionBloc",
                        "blocs": [
                            {"class": "TitleBloc", "title": "Featured"},
                            {"class": "DatasetBloc", "dataset": str(dataset.id)},
                        ],
                    }
                ],
            },
        )
        self.assert200(response)

        site = Site.objects.get(id=self.app.config["SITE_ID"])
        title, dataset_bloc = site.datasets_blocs[0].blocs
        assert isinstance(title, TitleBloc)
        assert title.title == "Featured"
        assert dataset_bloc.dataset.id == dataset.id

    def test_set_site_blocs_checks_layout(self):
        self.login(AdminFactory())
        response = self.patch(
            url_for("api.site"),
            {"datasets_blocs": [{"class": "TitleBloc", "title": "Not in a section"}]},
        )
        self.assert400(response)
        assert "TitleBloc is not allowed here" in response.get_data(as_text=True)
