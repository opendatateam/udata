from flask import url_for

from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory
from udata.core.pages.models import AccordionItemBloc, AccordionListBloc, Page
from udata.core.user.factories import AdminFactory
from udata.tests.api import APITestCase


class PageAPITest(APITestCase):
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

    def test_page_with_deleted_dataset(self):
        self.login(AdminFactory())
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
        page_id = response.json["id"]

        response = self.delete(url_for("api.dataset", dataset=datasets[0].id))
        self.assert204(response)

        response = self.get(url_for("api.page", page=page_id))
        self.assert200(response)

        tasks.purge_datasets()

        response = self.get(url_for("api.page", page=page_id))
        self.assert200(response)

    def test_hero_bloc(self):
        self.login()

        response = self.post(
            url_for("api.pages"),
            {
                "blocs": [
                    {
                        "class": "HeroBloc",
                        "title": "Welcome to our portal",
                        "description": "Discover our datasets",
                        "color": "primary",
                    }
                ],
            },
        )
        self.assert201(response)

        self.assertEqual("HeroBloc", response.json["blocs"][0]["class"])
        self.assertEqual("Welcome to our portal", response.json["blocs"][0]["title"])
        self.assertEqual("Discover our datasets", response.json["blocs"][0]["description"])
        self.assertEqual("primary", response.json["blocs"][0]["color"])

        page = Page.objects().first()
        response = self.get(url_for("api.page", page=page))
        self.assert200(response)

        self.assertEqual("HeroBloc", response.json["blocs"][0]["class"])
        self.assertEqual("Welcome to our portal", response.json["blocs"][0]["title"])
        self.assertEqual("Discover our datasets", response.json["blocs"][0]["description"])
        self.assertEqual("primary", response.json["blocs"][0]["color"])

    def test_accordion_bloc(self):
        self.login()
        datasets = DatasetFactory.create_batch(2)

        response = self.post(
            url_for("api.pages"),
            {
                "blocs": [
                    {
                        "class": "AccordionListBloc",
                        "title": "FAQ",
                        "description": "Frequently asked questions",
                        "items": [
                            {
                                "title": "What is udata?",
                                "content": [
                                    {
                                        "class": "LinksListBloc",
                                        "title": "Related links",
                                        "links": [
                                            {
                                                "title": "Documentation",
                                                "url": "https://doc.data.gouv.fr",
                                            },
                                        ],
                                    }
                                ],
                            },
                            {
                                "title": "How to use datasets?",
                                "content": [
                                    {
                                        "class": "DatasetsListBloc",
                                        "title": "Example datasets",
                                        "datasets": [str(d.id) for d in datasets],
                                    }
                                ],
                            },
                        ],
                    }
                ],
            },
        )
        self.assert201(response)

        bloc = response.json["blocs"][0]
        self.assertEqual("AccordionListBloc", bloc["class"])
        self.assertEqual("FAQ", bloc["title"])
        self.assertEqual("Frequently asked questions", bloc["description"])
        self.assertEqual(2, len(bloc["items"]))

        self.assertEqual("What is udata?", bloc["items"][0]["title"])
        self.assertEqual("LinksListBloc", bloc["items"][0]["content"][0]["class"])
        self.assertEqual("Documentation", bloc["items"][0]["content"][0]["links"][0]["title"])

        self.assertEqual("How to use datasets?", bloc["items"][1]["title"])
        self.assertEqual("DatasetsListBloc", bloc["items"][1]["content"][0]["class"])
        self.assertEqual(2, len(bloc["items"][1]["content"][0]["datasets"]))

        page = Page.objects().first()
        self.assertIsInstance(page.blocs[0], AccordionListBloc)
        self.assertIsInstance(page.blocs[0].items[0], AccordionItemBloc)
        self.assertEqual("What is udata?", page.blocs[0].items[0].title)

        response = self.get(url_for("api.page", page=page))
        self.assert200(response)
        self.assertEqual("AccordionListBloc", response.json["blocs"][0]["class"])
        self.assertEqual(2, len(response.json["blocs"][0]["items"]))

        response = self.put(
            url_for("api.page", page=page),
            {
                "blocs": [
                    {
                        "class": "AccordionListBloc",
                        "title": "Updated FAQ",
                        "items": [
                            {
                                "title": "Single question",
                                "content": [],
                            }
                        ],
                    }
                ],
            },
        )
        self.assert200(response)
        self.assertEqual("Updated FAQ", response.json["blocs"][0]["title"])
        self.assertIsNone(response.json["blocs"][0]["description"])
        self.assertEqual(1, len(response.json["blocs"][0]["items"]))
        self.assertEqual("Single question", response.json["blocs"][0]["items"][0]["title"])

    def test_accordion_bloc_cannot_be_nested(self):
        self.login()

        response = self.post(
            url_for("api.pages"),
            {
                "blocs": [
                    {
                        "class": "AccordionListBloc",
                        "title": "FAQ",
                        "items": [
                            {
                                "title": "Question",
                                "content": [
                                    {
                                        "class": "AccordionListBloc",
                                        "title": "Nested accordion",
                                        "items": [],
                                    }
                                ],
                            },
                        ],
                    }
                ],
            },
        )
        self.assert400(response)
