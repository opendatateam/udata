from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.pages.factories import PageFactory
from udata.core.pages.models import DatasetsListBloc
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert201, assert204, assert400


class PostsAPITest(APITestCase):
    def test_post_api_list(self):
        """It should fetch a post list from the API"""
        PostFactory.create_batch(3)
        draft = PostFactory(published=None)

        response = self.get(url_for("api.posts"))
        assert200(response)
        # Response should not contain the unpublished post
        assert len(response.json["data"]) == 3

        self.login(AdminFactory())

        response = self.get(url_for("api.posts"))
        assert200(response)

        assert len(response.json["data"]) == 3
        assert str(draft.id) not in [post["id"] for post in response.json["data"]]

        response = self.get(url_for("api.posts", with_drafts=True))
        assert200(response)

        assert len(response.json["data"]) == 4
        assert str(draft.id) in [post["id"] for post in response.json["data"]]

    def test_search_post(self):
        """It should fetch a post list from the API"""
        name_match = PostFactory(name="Foobar", published="2025-01-01")
        content_match = PostFactory(content="Foobar", published="2025-01-02")
        PostFactory(content="Something else")

        response = self.get(url_for("api.posts", q="Foobar"))
        assert200(response)
        assert len(response.json["data"]) == 2

        assert response.json["data"][0]["id"] == str(name_match.id)
        assert response.json["data"][1]["id"] == str(content_match.id)

        response = self.get(url_for("api.posts", q="Foobar", sort="-published"))
        assert200(response)
        assert len(response.json["data"]) == 2

        assert response.json["data"][1]["id"] == str(name_match.id)
        assert response.json["data"][0]["id"] == str(content_match.id)

    def test_post_api_get(self):
        """It should fetch a post from the API"""
        admin = AdminFactory()
        post = PostFactory(owner=admin)
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        owner = response.json["owner"]
        assert isinstance(owner, dict)
        assert owner["id"] == str(admin.id)

    def test_post_api_create(self):
        """It should create a post from the API"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        for dataset, expected in zip(post.datasets, data["datasets"]):
            assert str(dataset.id) == expected
        for reuse, expected in zip(post.reuses, data["reuses"]):
            assert str(reuse.id) == expected

    def test_post_api_update(self):
        """It should update a post from the API"""
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"
        self.login(AdminFactory())
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)
        assert Post.objects.count() == 1
        assert Post.objects.first().content == "new content"

    def test_post_api_update_with_related_dataset_and_reuse(self):
        """It should update a post from the API with related dataset and reuse"""
        self.login(AdminFactory())
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"

        # Add datasets
        data["datasets"] = [DatasetFactory().to_dict()]
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)

        # Add reuses to the post value returned by the previous api call
        data = response.json
        data["reuses"] = [ReuseFactory().to_dict()]
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)

        assert len(response.json["datasets"]) == 1
        assert len(response.json["reuses"]) == 1

    def test_post_api_delete(self):
        """It should delete a post from the API"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.delete(url_for("api.post", post=post))
        assert204(response)
        assert Post.objects.count() == 0

    def test_post_api_publish(self):
        """It should update a post from the API"""
        post = PostFactory(published=None)
        self.login(AdminFactory())
        response = self.post(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is not None

    def test_post_api_unpublish(self):
        """It should update a post from the API"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.delete(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is None

    def test_post_api_create_with_empty_credit_url(self):
        """It should create a post with an empty credit_url (converted to None)"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["credit_url"] = ""
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        assert post.credit_url is None

    def test_post_api_list_with_drafts_non_admin(self):
        """Non-admin users should not see drafts even with with_drafts=True"""
        PostFactory.create_batch(3)
        PostFactory(published=None)

        self.login(UserFactory())
        response = self.get(url_for("api.posts", with_drafts=True))
        assert200(response)
        assert len(response.json["data"]) == 3

    def test_post_api_create_with_blocs_body_type_and_page(self):
        """It should create a post with body_type='blocs' when content_as_page is provided"""
        page = PageFactory()
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["body_type"] = "blocs"
        data["content_as_page"] = str(page.id)
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        assert post.body_type == "blocs"
        assert post.content_as_page.id == page.id

    def test_post_api_create_with_blocs_body_type_without_page(self):
        """It should fail to create a post with body_type='blocs' without content_as_page"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["body_type"] = "blocs"
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert400(response)

    def test_post_api_get_with_blocs_returns_page_blocs(self):
        """It should return blocs from the associated page when fetching a post"""
        datasets = DatasetFactory.create_batch(2)
        bloc = DatasetsListBloc(title="Featured datasets", datasets=datasets)
        page = PageFactory(blocs=[bloc])
        post = PostFactory(body_type="blocs", content_as_page=page)
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["body_type"] == "blocs"
        assert "content_as_page" in response.json
        page_data = response.json["content_as_page"]
        assert "blocs" in page_data
        assert len(page_data["blocs"]) == 1
        assert page_data["blocs"][0]["class"] == "DatasetsListBloc"
        assert page_data["blocs"][0]["title"] == "Featured datasets"
        assert len(page_data["blocs"][0]["datasets"]) == 2

    def test_post_api_update_to_blocs_without_content_as_page(self):
        """It should fail to update body_type to 'blocs' without providing content_as_page"""
        post = PostFactory(body_type="markdown")
        self.login(AdminFactory())
        response = self.put(url_for("api.post", post=post), {"body_type": "blocs"})
        assert400(response)

    def test_post_api_update_to_blocs_with_content_as_page(self):
        """It should update body_type to 'blocs' when content_as_page is provided"""
        post = PostFactory(body_type="markdown")
        page = PageFactory()
        self.login(AdminFactory())
        response = self.put(
            url_for("api.post", post=post), {"body_type": "blocs", "content_as_page": str(page.id)}
        )
        assert200(response)
        post.reload()
        assert post.body_type == "blocs"
        assert post.content_as_page.id == page.id

    def test_post_api_update_remove_content_as_page_from_blocs_post(self):
        """It should fail to remove content_as_page from a post with body_type='blocs'"""
        page = PageFactory()
        post = PostFactory(body_type="blocs", content_as_page=page)
        self.login(AdminFactory())
        response = self.put(url_for("api.post", post=post), {"content_as_page": None})
        assert400(response)

    def test_post_api_update_body_type_preserves_content_as_page(self):
        """Switching from 'blocs' to 'markdown' preserves content_as_page so user can switch back"""
        page = PageFactory()
        post = PostFactory(body_type="blocs", content_as_page=page)
        self.login(AdminFactory())
        response = self.put(url_for("api.post", post=post), {"body_type": "markdown"})
        assert200(response)
        post.reload()
        assert post.body_type == "markdown"
        assert post.content_as_page.id == page.id
