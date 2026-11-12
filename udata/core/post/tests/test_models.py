from udata.core.edito_blocs.models import SectionBloc, TitleBloc
from udata.core.post.factories import PostFactory
from udata.tests.api import PytestOnlyDBTestCase


class PostTest(PytestOnlyDBTestCase):
    def test_blocs_body_type_without_blocs(self):
        post = PostFactory(body_type="blocs", blocs=[])
        post.reload()
        assert post.body_type == "blocs"
        assert post.blocs == []

    def test_blocs_body_type_with_blocs(self):
        bloc = SectionBloc(blocs=[TitleBloc(title="Test")])
        post = PostFactory(body_type="blocs", blocs=[bloc])
        post.reload()
        assert len(post.blocs) == 1
        assert post.blocs[0].blocs[0].title == "Test"
