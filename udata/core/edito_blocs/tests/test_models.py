import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DataserviceBloc,
    DataservicesListBloc,
    DatasetBloc,
    DatasetsListBloc,
    GridBloc,
    GridCell,
    ReuseBloc,
    ReusesListBloc,
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

# (factory, bloc class, its reference field, legacy list bloc class, its list field): one entry
# per referenceable type, so the purge is checked exhaustively.
CASES = [
    (DatasetFactory, DatasetBloc, "dataset", DatasetsListBloc, "datasets"),
    (ReuseFactory, ReuseBloc, "reuse", ReusesListBloc, "reuses"),
    (DataserviceFactory, DataserviceBloc, "dataservice", DataservicesListBloc, "dataservices"),
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

    @pytest.mark.parametrize("factory,bloc_cls,ref,_legacy_cls,_legacy_ref", CASES)
    def test_removes_the_bloc_in_a_section(self, factory, bloc_cls, ref, _legacy_cls, _legacy_ref):
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

    @pytest.mark.parametrize("factory,bloc_cls,ref,_legacy_cls,_legacy_ref", CASES)
    def test_removes_the_grid_cell_left_empty(
        self, factory, bloc_cls, ref, _legacy_cls, _legacy_ref
    ):
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

    @pytest.mark.parametrize("factory,_bloc_cls,_ref,legacy_cls,legacy_ref", CASES)
    def test_purges_legacy_blocs(self, factory, _bloc_cls, _ref, legacy_cls, legacy_ref):
        """Blocs not migrated yet to sections are purged too."""
        keep, remove = factory(), factory()
        self.store(
            lambda: [
                legacy_cls(title="t", **{legacy_ref: [remove, keep]}),
                AccordionListBloc(
                    title="a",
                    items=[
                        AccordionItemBloc(
                            title="i", content=[legacy_cls(**{legacy_ref: [remove, keep]})]
                        )
                    ],
                ),
            ]
        )

        purge_blocs_references(remove)

        for blocs in reload_blocs():
            top_level, accordion = blocs
            assert [r.id for r in getattr(top_level, legacy_ref)] == [keep.id]
            nested = accordion.items[0].content[0]
            assert [r.id for r in getattr(nested, legacy_ref)] == [keep.id]
