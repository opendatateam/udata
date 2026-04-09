from flask import g, url_for

from udata.core.edito_blocs.models import DatasetsListBloc, HeroBloc
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

    def test_get_site_with_x_fields_shows_blocs(self):
        # Trigger site creation via the API
        self.get(url_for("api.site"))
        site = Site.objects.get(id=self.app.config["SITE_ID"])
        site.datasets_blocs = [HeroBloc(title="Test hero")]
        site.save()

        # Invalidate the cached site in flask.g so it's reloaded from DB
        g.site = None

        response = self.get(url_for("api.site"), headers={"X-Fields": "{*}"})
        self.assert200(response)
        assert "datasets_blocs" in response.json
        assert len(response.json["datasets_blocs"]) == 1
        assert response.json["datasets_blocs"][0]["class"] == "HeroBloc"

    def test_set_site_blocs(self):
        self.login(AdminFactory())
        response = self.patch(
            url_for("api.site"),
            {
                "datasets_blocs": [
                    {
                        "class": "DatasetsListBloc",
                        "title": "Featured",
                        "datasets": [],
                    }
                ],
            },
        )
        self.assert200(response)

        site = Site.objects.get(id=self.app.config["SITE_ID"])
        assert len(site.datasets_blocs) == 1
        assert isinstance(site.datasets_blocs[0], DatasetsListBloc)
        assert site.datasets_blocs[0].title == "Featured"
