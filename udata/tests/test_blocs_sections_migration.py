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


def upgrade(blocs, colored=True):
    return migrations.get(MIGRATION).module.upgrade_legacy_blocs(blocs, colored)


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
            {"_id": "md", "_cls": "MarkdownBloc", "content": "A"},
            {"_id": "links", "_cls": "LinksListBloc", "links": []},
        ]
    )

    assert [bloc["_cls"] for bloc in blocs] == ["SectionBloc", "SectionBloc"]
    assert blocs[0]["blocs"] == [{"_id": "md", "_cls": "MarkdownBloc", "content": "A"}]
    assert blocs[1]["blocs"] == [{"_id": "links", "_cls": "LinksListBloc", "links": []}]


def test_hero_becomes_a_colored_section():
    hero = {
        "_id": "hero",
        "_cls": "HeroBloc",
        "title": "Hero",
        "description": "Description",
        "color": "green",
        "main_link_title": "Go",
        "main_link_url": "https://example.com",
    }

    (section,) = upgrade([hero])

    assert without_ids(section) == {
        "_cls": "SectionBloc",
        "color": "green",
        "blocs": [
            {"_cls": "TitleBloc", "title": "Hero", "subtitle": "Description"},
            {"_cls": "ButtonBloc", "title": "Go", "url": "https://example.com"},
        ],
    }
    # The section keeps the id of the hero it replaces.
    assert section["_id"] == "hero"


def test_hero_without_color_was_drawn_in_the_primary_one():
    (section,) = upgrade([{"_id": "hero", "_cls": "HeroBloc", "title": "Hero"}])

    assert without_ids(section) == {
        "_cls": "SectionBloc",
        "color": "primary",
        "blocs": [{"_cls": "TitleBloc", "title": "Hero"}],
    }


def test_hero_of_an_organization_gets_a_neutral_section():
    (section,) = upgrade([{"_id": "h", "_cls": "HeroBloc", "title": "H", "color": "green"}], False)

    assert "color" not in section


def test_hero_button_needs_a_title_and_a_url():
    """A main link was only shown with both, a button requires both."""
    hero = {"_id": "h", "_cls": "HeroBloc", "title": "H", "main_link_url": "https://e.com"}

    (section,) = upgrade([hero])

    assert [bloc["_cls"] for bloc in section["blocs"]] == ["TitleBloc"]


def test_links_list_with_a_paragraph_is_split_in_place():
    """The paragraph stays on the left of the links, with the button under it."""
    links = {
        "_id": "links",
        "_cls": "LinksListBloc",
        "paragraph": "P",
        "main_link_title": "Go",
        "main_link_url": "https://example.com",
        "links": [],
    }

    (section,) = upgrade([links])

    assert without_ids(section["blocs"]) == [
        {"_cls": "MarkdownBloc", "width": "1/2", "content": "P"},
        {"_cls": "LinksListBloc", "width": "1/2", "links": []},
        {"_cls": "ButtonBloc", "width": "1/2", "title": "Go", "url": "https://example.com"},
    ]


def test_links_list_without_paragraph_keeps_its_button_under_the_links():
    links = {
        "_id": "links",
        "_cls": "LinksListBloc",
        "paragraph": None,
        "main_link_title": "Go",
        "main_link_url": "https://example.com",
        "links": [],
    }

    (section,) = upgrade([links])

    assert without_ids(section["blocs"]) == [
        {"_cls": "LinksListBloc", "links": []},
        {"_cls": "ButtonBloc", "title": "Go", "url": "https://example.com"},
    ]


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
    """Without a title, an empty list shows nothing: it gets no section, a section cannot be
    empty."""
    blocs = upgrade(
        [
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "Soon", "datasets": []},
            {"_id": "2", "_cls": "ReusesListBloc"},
        ]
    )

    assert without_ids(blocs) == [
        {"_cls": "SectionBloc", "blocs": [{"_cls": "TitleBloc", "title": "Soon"}]},
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


def test_hero_in_an_accordion_item_becomes_its_title_and_its_button():
    hero = {
        "_id": "hero",
        "_cls": "HeroBloc",
        "title": "Hero",
        "description": "Description",
        "color": "green",
        "main_link_title": "Go",
        "main_link_url": "https://e.com",
    }

    blocs = upgrade(
        [{"_id": "acc", "_cls": "AccordionListBloc", "items": [{"title": "I", "content": [hero]}]}]
    )

    (item,) = without_ids(blocs)[0]["blocs"][0]["items"]
    assert item["content"] == [
        {"_cls": "TitleBloc", "title": "Hero", "subtitle": "Description"},
        {"_cls": "ButtonBloc", "title": "Go", "url": "https://e.com"},
    ]


def test_accordion_items_get_an_id():
    blocs = upgrade(
        [{"_id": "acc", "_cls": "AccordionListBloc", "items": [{"title": "A"}, {"title": "B"}]}]
    )

    items = blocs[0]["blocs"][0]["items"]
    assert all(item["_id"] for item in items)
    assert items[0]["_id"] != items[1]["_id"]


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
                HeroBloc(title="Hero", color="green"),
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
        # Only the sections of an organization keep a neutral background.
        for blocs, color in (
            (post.blocs, "green"),
            (organization.presentation_blocs, None),
            (site.reuses_blocs, "green"),
        ):
            hero, intro, featured = blocs
            assert isinstance(hero, SectionBloc)
            assert hero.color == color
            assert [bloc.title for bloc in hero.blocs] == ["Hero"]

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
