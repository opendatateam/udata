import mongoengine
import pytest

from udata.core.pages.factories import PageFactory
from udata.core.pages.models import Page
from udata.core.post.factories import PostFactory
from udata.tests.api import PytestOnlyDBTestCase


class PostTest(PytestOnlyDBTestCase):
    def test_page_deletion_raises_if_reference_still_exists(self):
        page = PageFactory()
        post = PostFactory(body_type="blocs", content_as_page=page)

        assert Page.objects().count() == 1

        with pytest.raises(mongoengine.errors.OperationError):
            page.delete()

        # Delete the post referencing the page before being able to delete the page itself
        post.delete()
        page.delete()

        assert Page.objects().count() == 0
