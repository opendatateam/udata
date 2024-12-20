import pytest
from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory
from udata.tests.helpers import assert200, assert201, assert204


@pytest.mark.usefixtures("clean_db")
class PostsAPITest:
    modules = []

    def test_post_api_list(self, api):
        """It should fetch a post list from the API"""
        PostFactory.create_batch(3)
        draft = PostFactory(published=None)

        response = api.get(url_for("api.posts"))
        assert200(response)
        # Response should not contain the unpublished post
        assert len(response.json["data"]) == 3

        api.login(AdminFactory())

        response = api.get(url_for("api.posts"))
        assert200(response)

        assert len(response.json["data"]) == 3
        assert str(draft.id) not in [post["id"] for post in response.json["data"]]

        response = api.get(url_for("api.posts", with_drafts=True))
        assert200(response)

        assert len(response.json["data"]) == 4
        assert str(draft.id) in [post["id"] for post in response.json["data"]]

    def test_post_api_get(self, api):
        """It should fetch a post from the API"""
        post = PostFactory()
        response = api.get(url_for("api.post", post=post))
        assert200(response)

    def test_post_api_create(self, api):
        """It should create a post from the API"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        api.login(AdminFactory())
        response = api.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        for dataset, expected in zip(post.datasets, data["datasets"]):
            assert str(dataset.id) == expected
        for reuse, expected in zip(post.reuses, data["reuses"]):
            assert str(reuse.id) == expected

    def test_post_api_update(self, api):
        """It should update a post from the API"""
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"
        api.login(AdminFactory())
        response = api.put(url_for("api.post", post=post), data)
        assert200(response)
        assert Post.objects.count() == 1
        assert Post.objects.first().content == "new content"

    def test_post_api_update_with_related_dataset_and_reuse(self, api):
        """It should update a post from the API with related dataset and reuse"""
        api.login(AdminFactory())
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"

        # Add datasets
        data["datasets"] = [DatasetFactory().to_dict()]
        response = api.put(url_for("api.post", post=post), data)
        assert200(response)

        # Add reuses to the post value returned by the previous api call
        data = response.json
        data["reuses"] = [ReuseFactory().to_dict()]
        response = api.put(url_for("api.post", post=post), data)
        assert200(response)

        assert len(response.json["datasets"]) == 1
        assert len(response.json["reuses"]) == 1

    def test_post_api_delete(self, api):
        """It should delete a post from the API"""
        post = PostFactory()
        with api.user(AdminFactory()):
            response = api.delete(url_for("api.post", post=post))
        assert204(response)
        assert Post.objects.count() == 0

    def test_post_api_publish(self, api):
        """It should update a post from the API"""
        post = PostFactory(published=None)
        api.login(AdminFactory())
        response = api.post(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is not None

    def test_post_api_unpublish(self, api):
        """It should update a post from the API"""
        post = PostFactory()
        api.login(AdminFactory())
        response = api.delete(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is None
