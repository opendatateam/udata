from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.pages.models import Page
from udata.tests.api import APITestCase


class PageAPITest(APITestCase):
    modules = []

    def test_api_create(self):
        self.login()
        datasets = DatasetFactory.create_batch(3)

        response = self.post(
            url_for("api.pages"),
            {
                "blocs": [
                    {
                        "type": "datasets_list",
                        "datasets": [str(d.id) for d in datasets],
                    }
                ],
            },
        )
        self.assert201(response)

        self.assertEqual(str(datasets[0].id), response.json["blocs"][0]["datasets"][0]["id"])
        self.assertEqual(str(datasets[1].id), response.json["blocs"][0]["datasets"][1]["id"])
        self.assertEqual(str(datasets[2].id), response.json["blocs"][0]["datasets"][2]["id"])

        page = Page.objects().first()
        self.assertEqual(datasets[0].id, page.blocs[0].datasets[0].id)
        self.assertEqual(datasets[1].id, page.blocs[0].datasets[1].id)
        self.assertEqual(datasets[2].id, page.blocs[0].datasets[2].id)
