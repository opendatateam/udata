from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    DatasetBloc,
    DatasetsListBloc,
    GridBloc,
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
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-21-blocs-sections.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


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
            title, grid = featured.blocs
            assert title.title == "Featured"
            assert isinstance(grid, GridBloc)
            assert [cell.width for cell in grid.cells] == ["1/2", "1/2"]
            assert [type(cell.blocs[0]) for cell in grid.cells] == [DatasetBloc, DatasetBloc]
            assert [cell.blocs[0].dataset.id for cell in grid.cells] == [d.id for d in datasets]
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
