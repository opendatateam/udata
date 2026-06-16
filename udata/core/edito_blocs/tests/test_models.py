import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DataservicesListBloc,
    DatasetsListBloc,
    ReusesListBloc,
    purge_blocs_references,
)
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.models import Site
from udata.tests.api import PytestOnlyDBTestCase

# (ref_field, factory, bloc_cls, site_blocs_field): one entry per referenceable type
# exposed through a blocs field, so the purge is checked exhaustively.
CASES = [
    ("datasets", DatasetFactory, DatasetsListBloc, "datasets_blocs"),
    ("reuses", ReuseFactory, ReusesListBloc, "reuses_blocs"),
    ("dataservices", DataserviceFactory, DataservicesListBloc, "dataservices_blocs"),
]


class PurgeBlocsReferencesTest(PytestOnlyDBTestCase):
    @pytest.mark.parametrize("ref_field,factory,bloc_cls,site_field", CASES)
    def test_purge_removes_top_level_bloc_reference(self, ref_field, factory, bloc_cls, site_field):
        keep = factory()
        remove = factory()
        bloc = bloc_cls(title="t", **{ref_field: [remove, keep]})
        PostFactory(body_type="blocs", blocs=[bloc])
        SiteFactory(id="test-site", **{site_field: [bloc]})

        purge_blocs_references(ref_field, remove.id)

        post_bloc = Post.objects.first().blocs[0]
        assert [r.id for r in getattr(post_bloc, ref_field)] == [keep.id]
        site_bloc = getattr(Site.objects.get(id="test-site"), site_field)[0]
        assert [r.id for r in getattr(site_bloc, ref_field)] == [keep.id]

    @pytest.mark.parametrize("ref_field,factory,bloc_cls,site_field", CASES)
    def test_purge_removes_accordion_nested_bloc_reference(
        self, ref_field, factory, bloc_cls, site_field
    ):
        keep = factory()
        remove = factory()
        nested = bloc_cls(title="t", **{ref_field: [remove, keep]})
        accordion = AccordionListBloc(
            title="a", items=[AccordionItemBloc(title="i", content=[nested])]
        )
        PostFactory(body_type="blocs", blocs=[accordion])
        SiteFactory(id="test-site", **{site_field: [accordion]})

        purge_blocs_references(ref_field, remove.id)

        post_inner = Post.objects.first().blocs[0].items[0].content[0]
        assert [r.id for r in getattr(post_inner, ref_field)] == [keep.id]
        site_inner = getattr(Site.objects.get(id="test-site"), site_field)[0].items[0].content[0]
        assert [r.id for r in getattr(site_inner, ref_field)] == [keep.id]
