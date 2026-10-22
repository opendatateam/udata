from bson import ObjectId
from flask import url_for
from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DatasetBloc,
    DatasetsListBloc,
    HeroBloc,
    MarkdownBloc,
    SectionBloc,
    TitleBloc,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.models import Site
from udata.db import migrations
from udata.tests.api import PytestOnlyAPITestCase, PytestOnlyDBTestCase
from udata.tests.helpers import assert200

MIGRATION = "2026-10-21-blocs-sections.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def upgrade(blocs):
    return migrations.get(MIGRATION).module.upgrade_legacy_blocs(blocs)


def without_ids(value):
    """Drop the generated `_id`s, which are random."""
    if isinstance(value, list):
        return [without_ids(item) for item in value]
    if isinstance(value, dict):
        return {k: without_ids(v) for k, v in value.items() if k != "_id"}
    return value


def test_each_legacy_bloc_gets_its_own_section():
    blocs = upgrade(
        [
            {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"},
            {"_id": "md", "_cls": "MarkdownBloc", "content": "A"},
            {"_id": "links", "_cls": "LinksListBloc", "links": []},
        ]
    )

    assert blocs[0] == {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"}
    assert [bloc["_cls"] for bloc in blocs[1:]] == ["SectionBloc", "SectionBloc"]
    assert blocs[1]["blocs"] == [{"_id": "md", "_cls": "MarkdownBloc", "content": "A"}]
    assert blocs[2]["blocs"] == [{"_id": "links", "_cls": "LinksListBloc", "links": []}]


def test_title_becomes_a_title_bloc():
    blocs = upgrade(
        [
            {"_id": "md", "_cls": "MarkdownBloc", "title": "T", "subtitle": "S", "content": "A"},
            {"_id": "explore", "_cls": "ExploreBloc", "title": "Only title", "resource_id": "r"},
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "T", "subtitle": "S"},
                {"_cls": "MarkdownBloc", "content": "A"},
            ],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "Only title"},
                {"_cls": "ExploreBloc", "resource_id": "r"},
            ],
        },
    ]
    # The converted bloc keeps its id.
    assert blocs[0]["blocs"][1]["_id"] == "md"


def test_subtitle_without_title_becomes_text():
    blocs = upgrade([{"_id": "md", "_cls": "MarkdownBloc", "subtitle": "S", "content": "A"}])

    assert without_ids(blocs[0]["blocs"]) == [
        {"_cls": "MarkdownBloc", "content": "S"},
        {"_cls": "MarkdownBloc", "content": "A"},
    ]


def test_blank_title_is_no_title():
    blocs = upgrade(
        [{"_id": "md", "_cls": "MarkdownBloc", "title": "  ", "subtitle": " ", "content": "A"}]
    )

    assert without_ids(blocs[0]["blocs"]) == [{"_cls": "MarkdownBloc", "content": "A"}]


def test_lists_become_one_bloc_per_object_keeping_their_columns():
    datasets = [ObjectId(), ObjectId()]
    reuse = ObjectId()
    dataservice = ObjectId()

    blocs = upgrade(
        [
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "Datasets", "datasets": datasets},
            {"_id": "2", "_cls": "ReusesListBloc", "reuses": [reuse]},
            {"_id": "3", "_cls": "DataservicesListBloc", "dataservices": [dataservice]},
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "Datasets"},
                *({"_cls": "DatasetBloc", "width": "1/2", "dataset": d} for d in datasets),
            ],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [{"_cls": "ReuseBloc", "width": "1/3", "reuse": reuse}],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [{"_cls": "DataserviceBloc", "width": "1/2", "dataservice": dataservice}],
        },
    ]


def test_empty_list_keeps_only_its_title():
    blocs = upgrade(
        [
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "Soon", "datasets": []},
            {"_id": "2", "_cls": "ReusesListBloc"},
        ]
    )

    assert without_ids(blocs) == [
        {"_cls": "SectionBloc", "blocs": [{"_cls": "TitleBloc", "title": "Soon"}]},
        {"_cls": "SectionBloc", "blocs": []},
    ]


def test_accordion_content_is_converted():
    dataset = ObjectId()

    blocs = upgrade(
        [
            {
                "_id": "acc",
                "_cls": "AccordionListBloc",
                "title": "FAQ",
                "description": "Questions",
                "items": [
                    {
                        "title": "Item",
                        "content": [
                            {
                                "_id": "list",
                                "_cls": "DatasetsListBloc",
                                "title": "In item",
                                "datasets": [dataset],
                            },
                            {"_id": "md", "_cls": "MarkdownBloc", "content": "A"},
                        ],
                    }
                ],
            }
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "FAQ", "subtitle": "Questions"},
                {
                    "_cls": "AccordionListBloc",
                    "items": [
                        {
                            "title": "Item",
                            "content": [
                                {"_cls": "TitleBloc", "title": "In item"},
                                {"_cls": "DatasetBloc", "width": "1/2", "dataset": dataset},
                                {"_cls": "MarkdownBloc", "content": "A"},
                            ],
                        }
                    ],
                },
            ],
        }
    ]


def test_upgrading_twice_gives_the_same_result():
    blocs = upgrade(
        [
            {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"},
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "T", "datasets": [ObjectId()]},
        ]
    )

    assert upgrade(blocs) == blocs


class BlocsSectionsMigrationTest(PytestOnlyDBTestCase):
    def test_legacy_blocs_are_moved_to_sections(self):
        datasets = DatasetFactory.create_batch(2)

        def legacy_blocs():
            return [
                HeroBloc(title="Hero"),
                MarkdownBloc(title="Intro", content="Hello"),
                DatasetsListBloc(title="Featured", datasets=datasets),
            ]

        post = PostFactory(body_type="blocs", blocs=legacy_blocs())
        organization = OrganizationFactory(presentation_blocs=legacy_blocs())
        SiteFactory(id="test-site", reuses_blocs=legacy_blocs())
        post.reload()
        last_modified = post.last_modified

        migrate()

        post.reload()
        organization.reload()
        site = Site.objects.get(id="test-site")
        for blocs in (post.blocs, organization.presentation_blocs, site.reuses_blocs):
            hero, intro, featured = blocs
            assert isinstance(hero, HeroBloc)
            assert hero.title == "Hero"

            assert isinstance(intro, SectionBloc)
            title, markdown = intro.blocs
            assert isinstance(title, TitleBloc)
            assert title.title == "Intro"
            assert isinstance(markdown, MarkdownBloc)
            assert (markdown.title, markdown.content) == (None, "Hello")

            assert isinstance(featured, SectionBloc)
            title, *objects = featured.blocs
            assert title.title == "Featured"
            assert [type(bloc) for bloc in objects] == [DatasetBloc, DatasetBloc]
            assert [bloc.width for bloc in objects] == ["1/2", "1/2"]
            assert [bloc.dataset.id for bloc in objects] == [d.id for d in datasets]
        # The content did not change for readers: the post is not marked as modified.
        assert post.last_modified == last_modified

    def test_running_twice_gives_the_same_result(self):
        post = PostFactory(
            body_type="blocs",
            blocs=[
                MarkdownBloc(title="Intro", content="Hello"),
                SectionBloc(blocs=[TitleBloc(title="Already upgraded")]),
            ],
        )

        migrate()
        post.reload()
        first = post.to_mongo()["blocs"]

        migrate()

        post.reload()
        assert post.to_mongo()["blocs"] == first
        assert post.blocs[1].blocs[0].title == "Already upgraded"


class BlocsSectionsMigrationAPITest(PytestOnlyAPITestCase):
    def test_deleted_objects_of_the_lists_are_left_out_at_read(self):
        """A dataset hard-deleted while listed becomes a bloc like the others: the API leaves
        it out, with the containers it leaves empty."""
        kept, deleted = DatasetFactory.create_batch(2)
        post = PostFactory(
            body_type="blocs",
            blocs=[
                DatasetsListBloc(title="Featured", datasets=[deleted, kept]),
                AccordionListBloc(
                    items=[
                        AccordionItemBloc(
                            title="Item", content=[DatasetsListBloc(datasets=[deleted])]
                        )
                    ]
                ),
            ],
        )
        Dataset._get_collection().delete_one({"_id": deleted.id})

        migrate()
        response = self.get(url_for("api.post", post=post))

        assert200(response)
        # The accordion only showed the deleted dataset: its section goes with it
        (featured,) = response.json["blocs"]
        title, dataset_bloc = featured["blocs"]
        assert title["title"] == "Featured"
        assert dataset_bloc["dataset"]["id"] == str(kept.id)
