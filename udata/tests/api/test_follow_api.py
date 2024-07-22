from flask import url_for

from udata.api import api
from udata.core.followers.api import FollowAPI
from udata.core.followers.signals import on_follow, on_unfollow
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
