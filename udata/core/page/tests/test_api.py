from datetime import datetime

from bson import ObjectId
from flask import url_for

from udata.core.edito_blocs.models import DatasetsListBloc
from udata.core.organization.factories import OrganizationFactory
from udata.core.page.factories import PageFactory
from udata.core.page.models import Page
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


class PageAPITest(PytestOnlyAPITestCase):
    def test_create_requires_auth(self):
        response = self.post(url_for("api.pages"), {"name": "A page"})
        assert401(response)

    def test_create_defaults_owner_to_current_user(self):
        user = self.login()
        response = self.post(
            url_for("api.pages"), {"name": "A page", "tags": ["a"], "description": "For SEO"}
        )
        assert201(response)
        assert response.json["description"] == "For SEO"
        assert response.json["owner"]["id"] == str(user.id)
        assert response.json["tags"] == ["a"]
        assert response.json["permissions"]["edit"] is True
        assert Page.objects.count() == 1

    def test_create_for_own_organization(self):
        user = self.login()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        response = self.post(url_for("api.pages"), {"name": "A page", "organization": str(org.id)})
        assert201(response)
        assert response.json["organization"]["id"] == str(org.id)

    def test_create_for_foreign_organization_is_rejected(self):
        self.login()
        org = OrganizationFactory()
        response = self.post(url_for("api.pages"), {"name": "A page", "organization": str(org.id)})
        assert400(response)

    def test_create_as_someone_else_is_rejected(self):
        self.login()
        other = UserFactory()
        response = self.post(url_for("api.pages"), {"name": "A page", "owner": str(other.id)})
        assert400(response)

    def test_list_hides_drafts_from_strangers(self):
        public = PageFactory()
        PageFactory(published=None)
        response = self.get(url_for("api.pages"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(public.id)]

    def test_list_shows_own_drafts(self):
        user = self.login()
        mine = PageFactory(owner=user, published=None)
        PageFactory(published=None)
        response = self.get(url_for("api.pages"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(mine.id)]

    def test_list_filter_by_tag(self):
        both = PageFactory(tags=["a", "b"])
        PageFactory(tags=["a"])
        response = self.get(url_for("api.pages", tag=["a", "b"]))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(both.id)]

    def test_get_by_id_and_slug(self):
        page = PageFactory(name="Hello")
        assert200(self.get(url_for("api.page", page=page.id)))
        response = self.get(url_for("api.page", page="hello"))
        assert200(response)
        assert response.json["id"] == str(page.id)

    def test_get_draft_is_404_for_strangers(self):
        owner = UserFactory()
        page = PageFactory(owner=owner, published=None)
        assert404(self.get(url_for("api.page", page=page)))
        self.login(owner)
        assert200(self.get(url_for("api.page", page=page)))

    def test_update_by_owner(self):
        user = self.login()
        page = PageFactory(owner=user)
        response = self.put(url_for("api.page", page=page), {"name": "New name"})
        assert200(response)
        page.reload()
        assert page.name == "New name"

    def test_update_by_stranger_is_forbidden(self):
        self.login()
        page = PageFactory(owner=UserFactory())
        assert403(self.put(url_for("api.page", page=page), {"name": "New name"}))

    def test_update_by_sysadmin(self):
        self.login(AdminFactory())
        page = PageFactory(owner=UserFactory())
        assert200(self.put(url_for("api.page", page=page), {"name": "New name"}))

    def test_update_cannot_change_owner(self):
        user = self.login()
        page = PageFactory(owner=user)
        other = UserFactory()
        response = self.put(url_for("api.page", page=page), {"owner": str(other.id)})
        assert400(response)

    def test_delete_by_owner(self):
        user = self.login()
        page = PageFactory(owner=user)
        assert204(self.delete(url_for("api.page", page=page)))
        assert Page.objects.count() == 0

    def test_delete_by_stranger_is_forbidden(self):
        self.login()
        page = PageFactory(owner=UserFactory())
        assert403(self.delete(url_for("api.page", page=page)))
        assert Page.objects.count() == 1

    def test_list_excludes_blocs_but_get_returns_them(self):
        page = PageFactory(blocs=[DatasetsListBloc(title="Test", datasets=[])])

        response = self.get(url_for("api.pages"))
        assert200(response)
        assert "blocs" not in response.json["data"][0]

        response = self.get(url_for("api.page", page=page))
        assert200(response)
        assert response.json["blocs"][0]["class"] == "DatasetsListBloc"

    def test_list_search_by_name(self):
        match = PageFactory(name="Budget participatif")
        PageFactory(name="Something else")
        response = self.get(url_for("api.pages", q="budget"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(match.id)]

    def test_delete_removes_topic_elements(self):
        user = self.login()
        topic = TopicFactory(owner=user)
        page = PageFactory(owner=user)
        TopicElement(topic=topic, element=page).save()
        assert204(self.delete(url_for("api.page", page=page)))
        assert TopicElement.objects(topic=topic).count() == 0
        assert200(self.get(url_for("apiv2.topic_elements", topic=topic)))

    def test_create_is_a_draft_and_published_is_read_only(self):
        self.login()
        response = self.post(
            url_for("api.pages"), {"name": "A page", "published": "2020-01-01T00:00:00"}
        )
        assert201(response)
        assert response.json["published"] is None

    def test_publish_and_unpublish(self):
        user = self.login()
        page = PageFactory(owner=user, published=None)

        response = self.post(url_for("api.publish_page", page=page))
        assert200(response)
        assert response.json["published"] is not None
        page.reload()
        assert page.is_visible

        response = self.delete(url_for("api.publish_page", page=page))
        assert200(response)
        assert response.json["published"] is None
        page.reload()
        assert not page.is_visible

    def test_publish_keeps_the_original_date(self):
        user = self.login()
        page = PageFactory(owner=user)
        page.reload()
        published = page.published
        assert200(self.post(url_for("api.publish_page", page=page)))
        page.reload()
        assert page.published == published

    def test_publish_by_stranger_is_forbidden(self):
        self.login()
        page = PageFactory(owner=UserFactory(), published=None)
        assert403(self.post(url_for("api.publish_page", page=page)))
        assert403(self.delete(url_for("api.publish_page", page=page)))

    def test_sort_by_published(self):
        old = PageFactory(published=datetime(2020, 1, 1))
        new = PageFactory(published=datetime(2024, 1, 1))
        response = self.get(url_for("api.pages", sort="-published"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(new.id), str(old.id)]

    def test_list_filter_by_topic(self):
        in_topic = PageFactory()
        PageFactory()
        topic = TopicFactory()
        TopicElement(topic=topic, element=in_topic).save()
        TopicElement(topic=TopicFactory(), element=PageFactory()).save()

        response = self.get(url_for("api.pages", topic=str(topic.id)))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(in_topic.id)]

    def test_list_filter_by_unknown_topic_is_empty(self):
        PageFactory()
        response = self.get(url_for("api.pages", topic=str(ObjectId())))
        assert200(response)
        assert response.json["data"] == []

    def test_list_filter_by_invalid_topic_is_rejected(self):
        assert400(self.get(url_for("api.pages", topic="not-an-id")))
