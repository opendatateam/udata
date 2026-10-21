from unittest import mock

import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs import models
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DataserviceBloc,
    DatasetBloc,
    GridBloc,
    GridCell,
    ReuseBloc,
    SectionBloc,
    TitleBloc,
    purge_blocs_references,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.models import Site
from udata.tests.api import PytestOnlyDBTestCase

# (factory, bloc class, its reference field): one entry per referenceable type, so the purge
# is checked exhaustively.
CASES = [
    (DatasetFactory, DatasetBloc, "dataset"),
    (ReuseFactory, ReuseBloc, "reuse"),
    (DataserviceFactory, DataserviceBloc, "dataservice"),
]


def reload_blocs():
    """The blocs of the post, the site and the organization of a test, from the database."""
    return [
        Post.objects.get().blocs,
        Site.objects.get(id="test-site").datasets_blocs,
        Organization.objects.get().presentation_blocs,
    ]


class PurgeBlocsReferencesTest(PytestOnlyDBTestCase):
    def store(self, make_blocs):
        PostFactory(body_type="blocs", blocs=make_blocs())
        SiteFactory(id="test-site", datasets_blocs=make_blocs())
        OrganizationFactory(presentation_blocs=make_blocs())

    @pytest.mark.parametrize("factory,bloc_cls,ref", CASES)
    def test_removes_the_bloc_in_a_section(self, factory, bloc_cls, ref):
        keep, remove = factory(), factory()
        self.store(
            lambda: [
                SectionBloc(
                    blocs=[
                        TitleBloc(title="t"),
                        bloc_cls(**{ref: remove}),
                        bloc_cls(**{ref: keep}),
                    ]
                )
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            title, kept = blocs[0].blocs
            assert title.title == "t"
            assert getattr(kept, ref).id == keep.id

    @pytest.mark.parametrize("factory,bloc_cls,ref", CASES)
    def test_removes_the_bloc_in_an_accordion_item(self, factory, bloc_cls, ref):
        keep, remove = factory(), factory()
        self.store(
            lambda: [
                SectionBloc(
                    blocs=[
                        AccordionListBloc(
                            items=[
                                AccordionItemBloc(
                                    title="i",
                                    content=[bloc_cls(**{ref: remove}), bloc_cls(**{ref: keep})],
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            content = blocs[0].blocs[0].items[0].content
            assert [getattr(bloc, ref).id for bloc in content] == [keep.id]

    @pytest.mark.parametrize("factory,bloc_cls,ref", CASES)
    def test_removes_the_grid_cell_left_empty(self, factory, bloc_cls, ref):
        keep, remove = factory(), factory()

        def grid(*objects):
            return GridBloc(
                cells=[GridCell(width="1/2", blocs=[bloc_cls(**{ref: o})]) for o in objects]
            )

        self.store(
            lambda: [
                SectionBloc(blocs=[grid(remove, keep)]),
                # A section only holding the removed object goes with it.
                SectionBloc(blocs=[grid(remove)]),
                SectionBloc(
                    blocs=[
                        AccordionListBloc(
                            items=[AccordionItemBloc(title="i", content=[grid(keep, remove)])]
                        )
                    ]
                ),
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            first, accordion_section = blocs
            assert [getattr(c.blocs[0], ref).id for c in first.blocs[0].cells] == [keep.id]
            cells = accordion_section.blocs[0].items[0].content[0].cells
            assert [getattr(c.blocs[0], ref).id for c in cells] == [keep.id]

    def test_keeps_a_cell_left_empty_on_purpose(self):
        remove = DatasetFactory()
        self.store(
            lambda: [
                SectionBloc(
                    blocs=[
                        GridBloc(
                            cells=[
                                GridCell(width="1/2", blocs=[]),
                                GridCell(width="1/2", blocs=[DatasetBloc(dataset=remove)]),
                            ]
                        )
                    ]
                )
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            assert [cell.blocs for cell in blocs[0].blocs[0].cells] == [[]]

    def test_leaves_other_types_alone(self):
        """A reuse and a dataset can share an id: only the blocs of the purged type go."""
        dataset = DatasetFactory()
        reuse = ReuseFactory(id=dataset.id)
        self.store(
            lambda: [SectionBloc(blocs=[DatasetBloc(dataset=dataset), ReuseBloc(reuse=reuse)])]
        )

        purge_blocs_references(reuse)

        for blocs in reload_blocs():
            assert [bloc.dataset.id for bloc in blocs[0].blocs] == [dataset.id]

    def test_removes_the_accordion_item_left_empty(self):
        keep, remove = DatasetFactory(), DatasetFactory()

        def grid(dataset):
            return GridBloc(cells=[GridCell(width="1/2", blocs=[DatasetBloc(dataset=dataset)])])

        self.store(
            lambda: [
                SectionBloc(
                    blocs=[
                        AccordionListBloc(
                            items=[
                                AccordionItemBloc(title="alone", content=[grid(remove)]),
                                AccordionItemBloc(title="kept", content=[grid(keep)]),
                            ]
                        )
                    ]
                )
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            assert [item.title for item in blocs[0].blocs[0].items] == ["kept"]

    def test_keeps_an_edit_saved_while_purging(self):
        """The purge rewrites the whole blocs field: an edit saved between its read and its
        write must not be lost."""
        remove = DatasetFactory()
        post = PostFactory(
            body_type="blocs", blocs=[SectionBloc(blocs=[DatasetBloc(dataset=remove)])]
        )
        without_blocs = models.without_blocs
        edited = []

        def edit_while_purging(*args, **kwargs):
            if not edited:
                # An editor saves the page right after the purge read it
                post.blocs = [
                    SectionBloc(blocs=[TitleBloc(title="Edited"), DatasetBloc(dataset=remove)])
                ]
                post.save()
                edited.append(True)
            return without_blocs(*args, **kwargs)

        with mock.patch.object(models, "without_blocs", side_effect=edit_while_purging):
            purge_blocs_references(remove)

        post.reload()
        assert [type(bloc).__name__ for bloc in post.blocs[0].blocs] == ["TitleBloc"]
        assert post.blocs[0].blocs[0].title == "Edited"
