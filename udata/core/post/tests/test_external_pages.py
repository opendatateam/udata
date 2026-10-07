from datetime import datetime

import pytest
from bson import ObjectId
from flask import url_for
from mongoengine.errors import ValidationError

from udata.core.edito_blocs.models import DatasetsListBloc
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.constants import EXTERNAL_PAGE
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.post.search import PostSearch
from udata.core.topic.factories import TopicFactory
from udata.core.topic.models import TopicElement
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Member
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import (
    assert200,
    assert201,
    assert204,
    assert400,
    assert401,
    assert403,
    assert404,
)


def external_page(**kwargs):
    kwargs.setdefault("body_type", "blocs")
    return PostFactory(kind=EXTERNAL_PAGE, content=None, datasets=[], reuses=[], **kwargs)


def payload(**kwargs):
    return {"name": "A page", "kind": EXTERNAL_PAGE, **kwargs}


class ExternalPageAPITest(PytestOnlyAPITestCase):
    def test_create_requires_auth(self):
        assert401(self.post(url_for("api.posts"), payload()))

    def test_create_defaults_owner_to_current_user(self):
        user = self.login()
        response = self.post(url_for("api.posts"), payload(tags=["a"], headline="For SEO"))
        assert201(response)
        assert response.json["headline"] == "For SEO"
        assert response.json["owner"]["id"] == str(user.id)
        assert response.json["tags"] == ["a"]
        assert response.json["permissions"]["edit"] is True
        assert Post.objects.count() == 1

    def test_create_defaults_to_blocs(self):
        self.login()
        response = self.post(url_for("api.posts"), payload())
        assert201(response)
        assert response.json["body_type"] == "blocs"

    def test_create_with_content_is_rejected(self):
        self.login()
        for extra in ({"body_type": "html", "content": "<script>x</script>"}, {"content": "Hi"}):
            assert400(self.post(url_for("api.posts"), payload(**extra)))
        assert Post.objects.count() == 0

    def test_create_has_no_web_url_on_the_main_site(self):
        self.login()
        response = self.post(url_for("api.posts"), payload())
        assert201(response)
        assert response.json["page"] is None

    def test_create_news_or_page_requires_sysadmin(self):
        self.login()
        for kind in ("news", "page"):
            response = self.post(url_for("api.posts"), {"name": "A post", "kind": kind})
            assert403(response)
        assert Post.objects.count() == 0

    def test_create_default_kind_requires_sysadmin(self):
        self.login()
        assert403(self.post(url_for("api.posts"), {"name": "A post", "content": "Hello"}))

    def test_create_for_own_organization(self):
        user = self.login()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        response = self.post(url_for("api.posts"), payload(organization=str(org.id)))
        assert201(response)
        assert response.json["organization"]["id"] == str(org.id)

    def test_create_for_foreign_organization_is_rejected(self):
        self.login()
        org = OrganizationFactory()
        assert400(self.post(url_for("api.posts"), payload(organization=str(org.id))))

    def test_create_as_someone_else_is_rejected(self):
        self.login()
        other = UserFactory()
        assert400(self.post(url_for("api.posts"), payload(owner=str(other.id))))

    def test_create_is_a_draft_and_published_is_read_only(self):
        self.login()
        response = self.post(url_for("api.posts"), payload(published="2020-01-01T00:00:00"))
        assert201(response)
        assert response.json["published"] is None

    def test_list_hides_drafts_from_strangers(self):
        public = external_page()
        external_page(published=None)
        response = self.get(url_for("api.posts", kind=EXTERNAL_PAGE))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(public.id)]

    def test_list_shows_own_drafts(self):
        user = self.login()
        mine = external_page(owner=user, published=None)
        external_page(published=None)
        response = self.get(url_for("api.posts", kind=EXTERNAL_PAGE))
        assert200(response)
        assert response.json["data"] == []

        response = self.get(url_for("api.posts", kind=EXTERNAL_PAGE, with_drafts=True))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(mine.id)]

    def test_list_never_shows_drafts_of_editorial_posts_to_owner(self):
        user = self.login()
        PostFactory(owner=user, published=None, kind="news")
        response = self.get(url_for("api.posts", with_drafts=True))
        assert200(response)
        assert response.json["data"] == []

    def test_list_excludes_blocs_but_get_returns_them(self):
        post = external_page(blocs=[DatasetsListBloc(title="Test", datasets=[])])

        response = self.get(url_for("api.posts", kind=EXTERNAL_PAGE))
        assert200(response)
        assert "blocs" not in response.json["data"][0]

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["blocs"][0]["class"] == "DatasetsListBloc"

    def test_get_draft_is_404_for_strangers(self):
        owner = UserFactory()
        post = external_page(owner=owner, published=None)
        assert404(self.get(url_for("api.post", post=post)))
        self.login(owner)
        assert200(self.get(url_for("api.post", post=post)))

    def test_get_draft_by_organization_member(self):
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        post = external_page(organization=org, published=None)
        assert404(self.get(url_for("api.post", post=post)))
        self.login(user)
        assert200(self.get(url_for("api.post", post=post)))

    def test_update_by_owner(self):
        user = self.login()
        post = external_page(owner=user)
        assert200(self.put(url_for("api.post", post=post), {"name": "New name"}))
        post.reload()
        assert post.name == "New name"

    def test_update_by_stranger_is_forbidden(self):
        self.login()
        post = external_page(owner=UserFactory())
        assert403(self.put(url_for("api.post", post=post), {"name": "New name"}))

    def test_update_by_sysadmin(self):
        self.login(AdminFactory())
        post = external_page(owner=UserFactory())
        assert200(self.put(url_for("api.post", post=post), {"name": "New name"}))

    def test_update_cannot_change_owner(self):
        user = self.login()
        post = external_page(owner=user)
        other = UserFactory()
        assert400(self.put(url_for("api.post", post=post), {"owner": str(other.id)}))

    def test_update_can_echo_the_same_kind(self):
        user = self.login()
        post = external_page(owner=user)
        response = self.put(url_for("api.post", post=post), {"kind": EXTERNAL_PAGE, "name": "New"})
        assert200(response)

    def test_owner_cannot_turn_an_external_page_into_a_page(self):
        user = self.login()
        post = external_page(owner=user)
        assert400(self.put(url_for("api.post", post=post), {"kind": "page"}))
        post.reload()
        assert post.kind == EXTERNAL_PAGE

    def test_sysadmin_cannot_turn_a_page_into_an_external_page(self):
        self.login(AdminFactory())
        post = PostFactory(kind="page")
        assert400(self.put(url_for("api.post", post=post), {"kind": EXTERNAL_PAGE}))

    def test_sysadmin_can_still_switch_between_news_and_page(self):
        self.login(AdminFactory())
        post = PostFactory(kind="news")
        assert200(self.put(url_for("api.post", post=post), {"kind": "page"}))

    def test_owner_cannot_edit_an_editorial_post(self):
        user = self.login()
        post = PostFactory(owner=user, kind="page")
        assert403(self.put(url_for("api.post", post=post), {"name": "New name"}))

    def test_delete_by_owner(self):
        user = self.login()
        post = external_page(owner=user)
        assert204(self.delete(url_for("api.post", post=post)))
        assert Post.objects.count() == 0

    def test_delete_by_stranger_is_forbidden(self):
        self.login()
        post = external_page(owner=UserFactory())
        assert403(self.delete(url_for("api.post", post=post)))
        assert Post.objects.count() == 1

    def test_delete_removes_topic_elements(self):
        user = self.login()
        topic = TopicFactory(owner=user)
        post = external_page(owner=user)
        TopicElement(topic=topic, element=post).save()
        assert204(self.delete(url_for("api.post", post=post)))
        assert TopicElement.objects(topic=topic).count() == 0
        assert200(self.get(url_for("apiv2.topic_elements", topic=topic)))

    def test_publish_and_unpublish(self):
        user = self.login()
        post = external_page(owner=user, published=None)

        response = self.post(url_for("api.publish_post", post=post))
        assert200(response)
        assert response.json["published"] is not None
        post.reload()
        assert post.is_visible

        response = self.delete(url_for("api.publish_post", post=post))
        assert200(response)
        assert response.json["published"] is None
        post.reload()
        assert not post.is_visible

    def test_publish_by_stranger_is_forbidden(self):
        self.login()
        post = external_page(owner=UserFactory(), published=None)
        assert403(self.post(url_for("api.publish_post", post=post)))
        assert403(self.delete(url_for("api.publish_post", post=post)))

    def test_image_upload_by_stranger_is_forbidden(self):
        self.login()
        post = external_page(owner=UserFactory())
        assert403(self.post(url_for("api.post_image", post=post)))

    def test_list_filter_by_topic(self):
        in_topic = external_page()
        external_page()
        topic = TopicFactory()
        TopicElement(topic=topic, element=in_topic).save()
        TopicElement(topic=TopicFactory(), element=external_page()).save()

        response = self.get(url_for("api.posts", topic=str(topic.id)))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(in_topic.id)]

    def test_list_filter_by_unknown_topic_is_empty(self):
        external_page()
        response = self.get(url_for("api.posts", topic=str(ObjectId())))
        assert200(response)
        assert response.json["data"] == []

    def test_list_filter_by_invalid_topic_is_rejected(self):
        assert400(self.get(url_for("api.posts", topic="not-an-id")))

    def test_sort_by_published(self):
        old = external_page(published=datetime(2020, 1, 1))
        new = external_page(published=datetime(2024, 1, 1))
        response = self.get(url_for("api.posts", kind=EXTERNAL_PAGE, sort="-published"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(new.id), str(old.id)]

    def test_list_excludes_external_pages_by_default(self):
        external_page()
        news = PostFactory(kind="news")
        response = self.get(url_for("api.posts"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(news.id)]

    def test_atom_feed_excludes_external_pages(self):
        page = external_page(name="Should stay out")
        response = self.get(url_for("api.recent_posts_atom_feed"))
        assert200(response)
        assert page.name not in response.data.decode()


class ExternalPageTopicElementTest(PytestOnlyAPITestCase):
    def test_add_post_element(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        post = external_page()
        response = self.post(
            url_for("apiv2.topic_elements", topic=topic),
            [{"element": {"class": "Post", "id": post.id}}],
        )
        assert201(response)
        assert response.json[0]["element"]["class"] == "Post"
        assert TopicElement.objects(topic=topic).first().element == post


class ExternalPageModelTest(PytestOnlyAPITestCase):
    def test_blocs_round_trip(self):
        post = external_page(blocs=[DatasetsListBloc(title="Test", datasets=[])])
        post.reload()
        assert len(post.blocs) == 1
        assert post.blocs[0].title == "Test"

    def test_clean_defaults_to_blocs(self):
        post = PostFactory(kind=EXTERNAL_PAGE, content=None)
        post.reload()
        assert post.body_type == "blocs"

    def test_clean_rejects_content(self):
        with pytest.raises(ValidationError):
            PostFactory(kind=EXTERNAL_PAGE, body_type="html", content="<b>x</b>")
        with pytest.raises(ValidationError):
            PostFactory(kind=EXTERNAL_PAGE, content="Hello")

    def test_kind_cannot_move_in_or_out_of_external_pages(self):
        page = external_page()
        page.kind = "page"
        page.content = "Hello"
        with pytest.raises(ValidationError):
            page.save()
        news = PostFactory(kind="news")
        news.kind = EXTERNAL_PAGE
        news.content = None
        with pytest.raises(ValidationError):
            news.save()
        news.reload()
        news.kind = "page"
        news.save()

    def test_visible_by_user_includes_own_drafts(self):
        user = UserFactory()
        mine = external_page(owner=user, published=None)
        external_page(published=None)
        public = external_page()
        visible = Post.objects.visible_by_user(user, Post.objects.visible()._query_obj)
        assert set(visible) == {mine, public}

    def test_not_indexable(self):
        assert PostSearch.is_indexable(PostFactory(kind="news"))
        assert not PostSearch.is_indexable(external_page())

    def test_not_in_mongo_search(self):
        PostFactory(kind="news")
        external_page()
        results = PostSearch.mongo_search({"q": None, "sort": None, "page": 1, "page_size": 20})
        assert [p.kind for p in results.objects] == ["news"] or [p.kind for p in results] == [
            "news"
        ]


class ExternalPagePermissionsTest(PytestOnlyAPITestCase):
    def test_owner_can_edit(self):
        user = self.login()
        post = external_page(owner=user)
        assert post.permissions["edit"].can()
        assert post.permissions["delete"].can()

    def test_stranger_cannot_edit(self):
        self.login()
        assert not external_page(owner=UserFactory()).permissions["edit"].can()

    def test_sysadmin_can_edit(self):
        self.login(AdminFactory())
        assert external_page(owner=UserFactory()).permissions["edit"].can()

    def test_org_editor_can_edit_but_not_member(self):
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        self.login(user)
        assert external_page(organization=org).permissions["edit"].can()

        other = UserFactory()
        org = OrganizationFactory(members=[Member(user=other, role="admin")])
        self.login(UserFactory())
        assert not external_page(organization=org).permissions["edit"].can()

    def test_owner_cannot_edit_editorial_post(self):
        user = self.login()
        assert not PostFactory(owner=user, kind="news").permissions["edit"].can()

    def test_draft_read(self):
        owner = UserFactory()
        post = external_page(owner=owner, published=None)
        self.login()
        assert not post.permissions["read"].can()
        self.login(owner)
        assert post.permissions["read"].can()

    def test_published_read(self):
        self.login()
        assert external_page().permissions["read"].can()
