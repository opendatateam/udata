from flask import url_for

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    DataservicesListBloc,
    DatasetsListBloc,
    ExploreBloc,
    ReusesListBloc,
)
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert201, assert204


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

    def test_post_api_list_excludes_blocs(self):
        """Blocs should not be included in the list endpoint"""
        bloc = DatasetsListBloc(title="Test", datasets=[])
        PostFactory(body_type="blocs", blocs=[bloc])

        response = self.get(url_for("api.posts"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert "blocs" not in response.json["data"][0]

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

    def test_post_api_create_with_blocs(self):
        """It should create a post with body_type='blocs' and inline blocs"""
        datasets = DatasetFactory.create_batch(2)
        self.login(AdminFactory())
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [
                {
                    "class": "DatasetsListBloc",
                    "title": "Featured datasets",
                    "datasets": [str(d.id) for d in datasets],
                }
            ],
        }
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        post = Post.objects.first()
        assert post.body_type == "blocs"
        assert len(post.blocs) == 1
        assert post.blocs[0].title == "Featured datasets"

    def test_post_api_get_with_blocs(self):
        """It should return blocs directly on the post"""
        datasets = DatasetFactory.create_batch(2)
        bloc = DatasetsListBloc(title="Featured datasets", datasets=datasets)
        post = PostFactory(body_type="blocs", blocs=[bloc])
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["body_type"] == "blocs"
        assert "blocs" in response.json
        assert len(response.json["blocs"]) == 1
        assert response.json["blocs"][0]["class"] == "DatasetsListBloc"
        assert response.json["blocs"][0]["title"] == "Featured datasets"
        assert len(response.json["blocs"][0]["datasets"]) == 2

    def test_post_api_get_blocs_only_returns_card_fields(self):
        """Blocs should return lightweight card representations, not full nested objects"""
        datasets = DatasetFactory.create_batch(2)
        reuses = ReuseFactory.create_batch(2)
        dataservices = DataserviceFactory.create_batch(2)
        post = PostFactory(
            body_type="blocs",
            blocs=[
                DatasetsListBloc(title="Datasets", datasets=datasets),
                ReusesListBloc(title="Reuses", reuses=reuses),
                DataservicesListBloc(title="Dataservices", dataservices=dataservices),
            ],
        )
        response = self.get(url_for("api.post", post=post))
        assert200(response)

        dataset_json = response.json["blocs"][0]["datasets"][0]
        assert "id" in dataset_json
        assert "title" in dataset_json
        assert "resources" not in dataset_json
        assert "community_resources" not in dataset_json

        reuse_json = response.json["blocs"][1]["reuses"][0]
        assert "id" in reuse_json
        assert "title" in reuse_json
        assert "datasets" not in reuse_json

        dataservice_json = response.json["blocs"][2]["dataservices"][0]
        assert "id" in dataservice_json
        assert "title" in dataservice_json
        assert "datasets" not in dataservice_json

    def test_post_api_create_with_explore_bloc(self):
        """It should create a post with an ExploreBloc referencing a resource"""
        dataset = DatasetFactory(visible=True)
        resource_id = dataset.resources[0].id
        self.login(AdminFactory())
        data = {
            "name": "Test explore post",
            "body_type": "blocs",
            "blocs": [
                {
                    "class": "ExploreBloc",
                    "title": "Explore the data",
                    "resource_id": str(resource_id),
                }
            ],
        }
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        post = Post.objects.first()
        assert len(post.blocs) == 1
        assert isinstance(post.blocs[0], ExploreBloc)
        assert post.blocs[0].resource_id == resource_id

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["blocs"][0]["class"] == "ExploreBloc"
        assert response.json["blocs"][0]["resource_id"] == str(resource_id)

    def test_post_api_filter_by_kind(self):
        """It should filter posts by kind"""
        news_post = PostFactory(kind="news")
        page_post = PostFactory(kind="page")

        response = self.get(url_for("api.posts", kind="news"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(news_post.id)

        response = self.get(url_for("api.posts", kind="page"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(page_post.id)

    def test_rss_feed_only_returns_news(self):
        """RSS feed should only return posts with kind=news"""
        news_post = PostFactory(kind="news")
        page_post = PostFactory(kind="page")

        response = self.get(url_for("api.recent_posts_atom_feed"))
        assert200(response)
        content = response.data.decode("utf-8")
        assert news_post.name in content
        assert page_post.name not in content
