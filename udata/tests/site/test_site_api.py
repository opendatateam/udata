from flask import url_for

from udata.core.pages.factories import PageFactory
from udata.core.site.models import Site
from udata.core.user.factories import AdminFactory
from udata.tests.api import APITestCase


class SiteAPITest(APITestCase):
    modules = []

    def test_get_site(self):
        response = self.get(url_for("api.site"))
        self.assert200(response)

        site = Site.objects.get(id=self.app.config["SITE_ID"])

        self.assertEqual(site.title, response.json["title"])

    def test_set_site(self):
        response = self.get(url_for("api.site"))
        self.assert200(response)

        site = Site.objects.get(id=self.app.config["SITE_ID"])
        ids = [p.id for p in PageFactory.create_batch(3)]
        self.login(AdminFactory())

        response = self.patch(
            url_for("api.site"),
            {
                "datasets_page": ids[0],
                "reuses_page": ids[1],
                "dataservices_page": ids[2],
            },
        )

        self.assert200(response)
        self.assertEqual(response.json["title"], site.title)

        site = Site.objects.get(id=self.app.config["SITE_ID"])

        self.assertEqual(site.datasets_page.id, ids[0])
        self.assertEqual(site.reuses_page.id, ids[1])
        self.assertEqual(site.dataservices_page.id, ids[2])
