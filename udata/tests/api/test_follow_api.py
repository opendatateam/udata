from flask import url_for

from udata.api import api
from udata.core.dataset.factories import DatasetFactory
from udata.core.followers.api import FollowAPI
from udata.core.followers.signals import on_follow, on_unfollow
from udata.core.user.factories import UserFactory
from udata.models import Follow, db

from . import APITestCase


class FakeModel(db.Document):
    name = db.StringField()

    def count_followers(self):
        pass


@api.route("/fake/<id>/follow/", endpoint="follow_fake")
class FollowFakeAPI(FollowAPI):
    model = FakeModel


class FollowAPITest(APITestCase):
    def setUp(self):
        self.signal_emitted = False

    def handler(self, sender):
        self.assertIsInstance(sender, Follow)
        self.signal_emitted = True

    def test_follow_list(self):
        """It should list on GET"""
        user = self.login()
        to_follow = FakeModel.objects.create()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.get(url_for("api.follow_fake", id=to_follow.id))

        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json["total"], nb_followers)
        self.assertEqual(nb_followers, 1)

    def test_follow_list_user(self):
        """It should list with user arg on GET"""
        user = self.login()
        to_follow = FakeModel.objects.create()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.get(url_for("api.follow_fake", id=to_follow.id, user=user.id))

        self.assert200(response)

        is_following = Follow.objects.is_following(user, to_follow)

        self.assertEqual(response.json["total"], 1)
        self.assertTrue(is_following)

    def test_follow_list_other_user(self):
        """It should list with user arg on GET"""
        user = self.login()
        other_user = UserFactory()
        to_follow = FakeModel.objects.create()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.get(url_for("api.follow_fake", id=to_follow.id, user=other_user.id))

        self.assert200(response)

        following = Follow.objects.is_following(other_user, to_follow)

        self.assertFalse(following)

    def test_follow(self):
        """It should follow on POST"""
        user = self.login()
        to_follow = FakeModel.objects.create()

        with on_follow.connected_to(self.handler):
            response = self.post(url_for("api.follow_fake", id=to_follow.id))

        self.assert201(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json["followers"], nb_followers)
        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(), Follow)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)
        self.assertTrue(self.signal_emitted)

    def test_follow_already_followed(self):
        """It should do nothing when following an already followed object"""
        user = self.login()
        to_follow = FakeModel.objects.create()
        Follow.objects.create(follower=user, following=to_follow)

        with on_follow.connected_to(self.handler):
            response = self.post(url_for("api.follow_fake", id=to_follow.id))

        self.assertStatus(response, 200)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)
        self.assertFalse(self.signal_emitted)

    def test_unfollow(self):
        """It should unfollow on DELETE"""
        user = self.login()
        to_follow = FakeModel.objects.create()
        Follow.objects.create(follower=user, following=to_follow)

        with on_unfollow.connected_to(self.handler):
            response = self.delete(url_for("api.follow_fake", id=to_follow.id))

        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json["followers"], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)
        self.assertTrue(self.signal_emitted)

    def test_unfollow_not_existing(self):
        """It should raise 404 when trying to unfollow a not followed object"""
        self.login()
        to_follow = FakeModel.objects.create()

        response = self.delete(url_for("api.follow_fake", id=to_follow.id))
        self.assert404(response)

    def test_get_followed_datasets_for_user(self):
        user_a = UserFactory()
        user_b = UserFactory()
        dataset_a = DatasetFactory()
        dataset_b = DatasetFactory()
        dataset_c = DatasetFactory()

        Follow.objects.create(follower=user_a, following=dataset_a)
        Follow.objects.create(follower=user_a, following=dataset_b)
        Follow.objects.create(follower=user_b, following=dataset_a)
        Follow.objects.create(follower=user_b, following=dataset_b)
        Follow.objects.create(follower=user_b, following=dataset_c)

        response = self.get(url_for("api.datasets", followed_by=user_a.id))
        self.assertEqual(response.json["total"], 2)

        response = self.get(url_for("api.datasets", followed_by=user_b.id))
        self.assertEqual(response.json["total"], 3)
