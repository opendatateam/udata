from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.pages.models import Page
from udata.tests.api import APITestCase


class PageAPITest(APITestCase):
    modules = []

    def test_create_get_update(self):
        self.login()
        datasets = DatasetFactory.create_batch(3)

        response = self.post(
            url_for("api.pages"),
            {
                "blocs": [
                    {
                        "class": "DatasetsListBloc",
                        "title": "My awesome title",
                        "datasets": [str(d.id) for d in datasets],
                    }
                ],
            },
        )
        self.assert201(response)

        self.assertEqual(len(response.json["blocs"][0]["datasets"]), 3)
        self.assertEqual("DatasetsListBloc", response.json["blocs"][0]["class"])
        self.assertEqual("My awesome title", response.json["blocs"][0]["title"])
        self.assertIsNone(response.json["blocs"][0]["subtitle"])
        self.assertEqual(str(datasets[0].id), response.json["blocs"][0]["datasets"][0]["id"])
        self.assertEqual(str(datasets[1].id), response.json["blocs"][0]["datasets"][1]["id"])
        self.assertEqual(str(datasets[2].id), response.json["blocs"][0]["datasets"][2]["id"])

        page = Page.objects().first()
        self.assertEqual(str(page.id), response.json["id"])
        self.assertEqual("My awesome title", page.blocs[0].title)
        self.assertIsNone(page.blocs[0].subtitle)
        self.assertEqual(datasets[0].id, page.blocs[0].datasets[0].id)
        self.assertEqual(datasets[1].id, page.blocs[0].datasets[1].id)
        self.assertEqual(datasets[2].id, page.blocs[0].datasets[2].id)

        response = self.get(url_for("api.page", page=page))
        self.assert200(response)

        self.assertEqual(len(response.json["blocs"][0]["datasets"]), 3)
        self.assertEqual("DatasetsListBloc", response.json["blocs"][0]["class"])
        self.assertEqual("My awesome title", response.json["blocs"][0]["title"])
        self.assertIsNone(response.json["blocs"][0]["subtitle"])
        self.assertEqual(str(datasets[0].id), response.json["blocs"][0]["datasets"][0]["id"])
        self.assertEqual(str(datasets[1].id), response.json["blocs"][0]["datasets"][1]["id"])
        self.assertEqual(str(datasets[2].id), response.json["blocs"][0]["datasets"][2]["id"])

        response = self.put(
            url_for("api.page", page=page),
            {
                "blocs": [
                    {
                        "class": "DatasetsListBloc",
                        "title": "My awesome title",
                        "subtitle": "more information",
                        "datasets": [{"id": str(datasets[2].id)}],
                    }
                ],
            },
        )
        self.assert200(response)

        self.assertEqual("DatasetsListBloc", response.json["blocs"][0]["class"])
        self.assertEqual("My awesome title", response.json["blocs"][0]["title"])
        self.assertEqual("more information", response.json["blocs"][0]["subtitle"])
        self.assertEqual(len(response.json["blocs"][0]["datasets"]), 1)
        self.assertEqual(str(datasets[2].id), response.json["blocs"][0]["datasets"][0]["id"])
