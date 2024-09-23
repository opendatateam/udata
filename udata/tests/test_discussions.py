from datetime import datetime

import pytest
from flask import url_for
from werkzeug.test import TestResponse

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.discussions.metrics import update_discussions_metric  # noqa
from udata.core.discussions.models import Discussion, Message
from udata.core.discussions.notifications import discussions_notifications
from udata.core.discussions.signals import (
    on_discussion_closed,
    on_discussion_deleted,
    on_new_discussion,
    on_new_discussion_comment,
)
from udata.core.discussions.tasks import (
    notify_discussion_closed,
    notify_new_discussion,
    notify_new_discussion_comment,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization
from udata.core.reuse.factories import ReuseFactory
from udata.core.spam.signals import on_new_potential_spam
from udata.core.user.factories import AdminFactory, UserFactory
from udata.core.user.models import User
from udata.models import Dataset, Member
from udata.tests.helpers import capture_mails
from udata.utils import faker

from . import DBTestMixin, TestCase
from .api import APITestCase
from .helpers import assert_emit, assert_not_emit


class DiscussionsTest(APITestCase):
    modules = []

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_new_discussion(self):
        user = self.login()
        dataset = Dataset.objects.create(title="Test dataset")

        with assert_emit(on_new_discussion):
            response = self.post(
                url_for("api.discussions"),
                {
                    "title": "test title",
                    "comment": "bla bla",
                    "subject": {
                        "class": "Dataset",
                        "id": dataset.id,
                    },
                },
            )
            self.assert201(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()["discussions"], 1)

        discussions = Discussion.objects(subject=dataset)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertEqual(discussion.user, user)
        self.assertEqual(len(discussion.discussion), 1)
        self.assertIsNotNone(discussion.created)
        self.assertIsNone(discussion.closed)
        self.assertIsNone(discussion.closed_by)
        self.assertEqual(discussion.title, "test title")
        self.assertFalse(discussion.is_spam())

        message = discussion.discussion[0]
        self.assertEqual(message.content, "bla bla")
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)
        self.assertFalse(message.is_spam())

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_spam_in_new_discussion_title(self):
        self.login()
        dataset = Dataset.objects.create(title="Test dataset")

        with assert_not_emit(on_new_discussion):
            discussion_id = None

            def check_signal(args):
                self.assertIsNotNone(discussion_id)
                self.assertIn(
                    f"http://local.test/api/1/datasets/{dataset.slug}/#discussion-{discussion_id}",
                    args[1]["message"],
                )

            with assert_emit(on_new_potential_spam, assertions_callback=check_signal):
                response = self.post(
                    url_for("api.discussions"),
                    {
                        "title": "spam and blah",
                        "comment": "bla bla",
                        "subject": {
                            "class": "Dataset",
                            "id": dataset.id,
                        },
                    },
                )
                self.assertStatus(response, 201)
                discussion_id = response.json["id"]

        discussions = Discussion.objects(subject=dataset)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertTrue(discussion.is_spam())
        self.assertFalse(discussion.discussion[0].is_spam())
        self.assertTrue("signal_new" in discussion.spam.callbacks)

        with assert_not_emit(on_new_discussion):
            response = self.delete(url_for("api.discussion_spam", id=discussion.id))
            self.assertStatus(response, 403)
            self.assertTrue(discussion.reload().is_spam())

        self.login(AdminFactory())
        response = self.get(url_for("api.spam"))
        self.assertStatus(response, 200)
        self.assertEqual(
            response.json,
            [
                {
                    "message": discussion.spam_report_message([discussion]),
                }
            ],
        )

        with assert_emit(on_new_discussion):
            response = self.delete(url_for("api.discussion_spam", id=discussion.id))
            self.assertStatus(response, 200)
            self.assertFalse(discussion.reload().is_spam())

        # Adding a new comment / modifying the not spam discussion
        response = self.post(
            url_for("api.discussion", id=discussion.id), {"comment": "A new normal comment"}
        )
        self.assertStatus(response, 200)
        self.assertFalse(discussion.reload().is_spam())

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_spam_by_owner(self):
        user = self.login()
        dataset = Dataset.objects.create(title="Test dataset", owner=user)

        with assert_not_emit(on_new_potential_spam):
            response = self.post(
                url_for("api.discussions"),
                {
                    "title": "spam and blah",
                    "comment": "bla bla",
                    "subject": {
                        "class": "Dataset",
                        "id": dataset.id,
                    },
                },
            )
            self.assertStatus(response, 201)

        with assert_not_emit(on_new_potential_spam):
            response = self.post(
                url_for("api.discussion", id=response.json["id"]),
                {"comment": "A comment with spam by owner"},
            )
            self.assertStatus(response, 200)

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_spam_in_new_discussion_comment(self):
        self.login()
        dataset = Dataset.objects.create(title="Test dataset")

        with assert_not_emit(on_new_discussion):
            with assert_emit(on_new_potential_spam):
                response = self.post(
                    url_for("api.discussions"),
                    {
                        "title": "title and blah",
                        "comment": "bla bla spam",
                        "subject": {
                            "class": "Dataset",
                            "id": dataset.id,
                        },
                    },
                )
                self.assertStatus(response, 201)

        discussions = Discussion.objects(subject=dataset)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertTrue(discussion.is_spam())
        self.assertFalse(discussion.discussion[0].is_spam())

    def test_new_discussion_missing_comment(self):
        self.login()
        dataset = Dataset.objects.create(title="Test dataset")

        response = self.post(
            url_for("api.discussions"),
            {
                "title": "test title",
                "subject": {
                    "class": "Dataset",
                    "id": dataset.id,
                },
            },
        )
        self.assertStatus(response, 400)

    def test_new_discussion_missing_title(self):
        self.login()
        dataset = Dataset.objects.create(title="Test dataset")

        response = self.post(
            url_for("api.discussions"),
            {
                "comment": "bla bla",
                "subject": {
                    "class": "Dataset",
                    "id": dataset.id,
                },
            },
        )
        self.assertStatus(response, 400)

    def test_new_discussion_missing_subject(self):
        self.login()
        response = self.post(
            url_for("api.discussions"), {"title": "test title", "comment": "bla bla"}
        )
        self.assertStatus(response, 400)

    def test_new_discussion_with_extras(self):
        user = self.login()
        dataset = Dataset.objects.create(title="Test dataset", extras={"key": "value"})

        with assert_emit(on_new_discussion):
            response = self.post(
                url_for("api.discussions"),
                {
                    "title": "test title",
                    "comment": "bla bla",
                    "subject": {
                        "class": "Dataset",
                        "id": dataset.id,
                    },
                    "extras": {"key": "value"},
                },
            )
        self.assert201(response)

        discussions = Discussion.objects(subject=dataset)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertEqual(discussion.user, user)
        self.assertEqual(len(discussion.discussion), 1)
        self.assertEqual(discussion.title, "test title")
        self.assertEqual(discussion.extras, {"key": "value"})

        message = discussion.discussion[0]
        self.assertEqual(message.content, "bla bla")
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)

    def test_list_discussions(self):
        dataset = Dataset.objects.create(title="Test dataset")
        open_discussions = []
        closed_discussions = []
        for i in range(2):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
                closed=datetime.utcnow(),
                closed_by=user,
            )
            closed_discussions.append(discussion)

        response = self.get(url_for("api.discussions"))
        self.assert200(response)

        self.assertEqual(len(response.json["data"]), len(open_discussions + closed_discussions))

    def test_list_discussions_closed_filter(self):
        dataset = Dataset.objects.create(title="Test dataset")
        open_discussions = []
        closed_discussions = []
        for i in range(2):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
                closed=datetime.utcnow(),
                closed_by=user,
            )
            closed_discussions.append(discussion)

        response = self.get(url_for("api.discussions", closed=True))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), len(closed_discussions))
        for discussion in response.json["data"]:
            self.assertIsNotNone(discussion["closed"])

    def test_list_discussions_for(self):
        dataset = DatasetFactory()
        discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
            )
            discussions.append(discussion)
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Discussion.objects.create(
            subject=DatasetFactory(),
            user=user,
            title="test discussion {}".format(i),
            discussion=[message],
        )

        kwargs = {"for": str(dataset.id)}
        response = self.get(url_for("api.discussions", **kwargs))
        self.assert200(response)

        self.assertEqual(len(response.json["data"]), len(discussions))

    def assertIdIn(self, json_data: dict, id_: str) -> None:
        for item in json_data:
            if item["id"] == id_:
                return
        self.fail(f"id {id_} not in {json_data}")

    def test_list_discussions_org_does_not_exist(self) -> None:
        response: TestResponse = self.get(url_for("api.discussions", org="bad org id"))
        self.assert404(response)

    def test_list_discussions_org(self) -> None:
        organization: Organization = OrganizationFactory()
        user: User = UserFactory()
        _discussion: Discussion = DiscussionFactory(user=user)
        dataset = DatasetFactory(organization=organization)
        dataservice = DataserviceFactory(organization=organization)
        reuse = ReuseFactory(organization=organization)
        discussion_for_dataset: Discussion = DiscussionFactory(subject=dataset, user=user)
        discussion_for_dataservice: Discussion = DiscussionFactory(subject=dataservice, user=user)
        discussion_for_reuse: Discussion = DiscussionFactory(subject=reuse, user=user)

        response: TestResponse = self.get(url_for("api.discussions", org=organization.id))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 3)
        self.assertIdIn(response.json["data"], str(discussion_for_dataset.id))
        self.assertIdIn(response.json["data"], str(discussion_for_dataservice.id))
        self.assertIdIn(response.json["data"], str(discussion_for_reuse.id))

    def test_list_discussions_sort(self) -> None:
        user: User = UserFactory()
        sorting_keys_dict: dict = {
            "title": ["aaa", "bbb"],
            "created": ["2023-12-12", "2024-01-01"],
            "closed": ["2023-12-12", "2024-01-01"],
        }
        for sorting_key, values in sorting_keys_dict.items():
            discussion1: Discussion = DiscussionFactory(user=user, **{sorting_key: values[0]})
            discussion2: Discussion = DiscussionFactory(user=user, **{sorting_key: values[1]})

            response: TestResponse = self.get(url_for("api.discussions", sort=sorting_key))
            self.assert200(response)
            self.assertEqual(len(response.json["data"]), 2)
            self.assertEqual(response.json["data"][0]["id"], str(discussion1.id))
            self.assertEqual(response.json["data"][1]["id"], str(discussion2.id))

            # Reverse sort
            response: TestResponse = self.get(url_for("api.discussions", sort="-" + sorting_key))
            self.assert200(response)
            self.assertEqual(len(response.json["data"]), 2)
            self.assertEqual(response.json["data"][0]["id"], str(discussion2.id))
            self.assertEqual(response.json["data"][1]["id"], str(discussion1.id))

            # Clean slate
            Discussion.objects.delete()

    def test_list_discussions_user(self):
        dataset = DatasetFactory()
        discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title="test discussion {}".format(i),
                discussion=[message],
            )
            discussions.append(discussion)
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Discussion.objects.create(
            subject=DatasetFactory(),
            user=user,
            title="test discussion {}".format(i + 1),
            discussion=[message],
        )

        kwargs = {"user": str(user.id)}
        response = self.get(url_for("api.discussions", **kwargs))
        self.assert200(response)

        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["user"]["id"], str(user.id))

    def test_get_discussion(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )

        response = self.get(url_for("api.discussion", **{"id": discussion.id}))
        self.assert200(response)

        data = response.json

        self.assertEqual(data["subject"]["class"], "Dataset")
        self.assertEqual(data["subject"]["id"], str(dataset.id))
        self.assertEqual(data["user"]["id"], str(user.id))
        self.assertEqual(data["title"], "test discussion")
        self.assertIsNotNone(data["created"])
        self.assertEqual(len(data["discussion"]), 1)
        self.assertEqual(data["discussion"][0]["content"], "bla bla")
        self.assertEqual(data["discussion"][0]["posted_by"]["id"], str(user.id))
        self.assertIsNotNone(data["discussion"][0]["posted_on"])

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_add_comment_to_discussion(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        poster = self.login()
        with assert_emit(on_new_discussion_comment):
            response = self.post(
                url_for("api.discussion", id=discussion.id), {"comment": "new bla bla"}
            )
        self.assert200(response)

        dataset.reload()
        discussion.reload()
        self.assertEqual(dataset.get_metrics()["discussions"], 1)

        data = response.json

        self.assertEqual(data["subject"]["class"], "Dataset")
        self.assertEqual(data["subject"]["id"], str(dataset.id))
        self.assertEqual(data["user"]["id"], str(user.id))
        self.assertEqual(data["title"], "test discussion")
        self.assertIsNotNone(data["created"])
        self.assertIsNone(data["closed"])
        self.assertIsNone(data["closed_by"])
        self.assertEqual(len(data["discussion"]), 2)
        self.assertEqual(data["discussion"][1]["content"], "new bla bla")
        self.assertEqual(data["discussion"][1]["posted_by"]["id"], str(poster.id))
        self.assertIsNotNone(data["discussion"][1]["posted_on"])
        self.assertFalse(discussion.discussion[1].is_spam())

    @pytest.mark.options(SPAM_WORDS=["spam"])
    def test_add_spam_comment_to_discussion(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        self.login()
        with assert_not_emit(on_new_discussion_comment):

            def check_signal(args):
                self.assertIn(discussion.external_url, args[1]["message"])

            with assert_emit(on_new_potential_spam, assertions_callback=check_signal):
                response = self.post(
                    url_for("api.discussion", id=discussion.id), {"comment": "spam new bla bla"}
                )
                self.assert200(response)

        discussion.reload()
        self.assertFalse(discussion.is_spam())
        self.assertTrue(discussion.discussion[1].is_spam())
        self.assertTrue("signal_comment" in discussion.discussion[1].spam.callbacks)

        self.login(AdminFactory())
        response = self.get(url_for("api.spam"))
        self.assertStatus(response, 200)
        self.assertEqual(
            response.json,
            [
                {
                    "message": discussion.spam_report_message([discussion]),
                }
            ],
        )

        with assert_emit(on_new_discussion_comment):
            response = self.delete(url_for("api.discussion_comment_spam", id=discussion.id, cidx=1))
            self.assertStatus(response, 200)
            self.assertFalse(discussion.reload().discussion[1].is_spam())

        response = self.post(
            url_for("api.discussion", id=discussion.id), {"comment": "New comment"}
        )
        self.assert200(response)

        # The spam comment marked as no spam is still a no spam
        self.assertFalse(discussion.reload().discussion[1].is_spam())

    def test_close_discussion(self):
        owner = self.login()
        user = UserFactory()
        dataset = Dataset.objects.create(title="Test dataset", owner=owner)
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        with assert_emit(on_discussion_closed):
            response = self.post(
                url_for("api.discussion", id=discussion.id),
                {"comment": "close bla bla", "close": True},
            )
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()["discussions"], 0)

        data = response.json

        self.assertEqual(data["subject"]["class"], "Dataset")
        self.assertEqual(data["subject"]["id"], str(dataset.id))
        self.assertEqual(data["user"]["id"], str(user.id))
        self.assertEqual(data["title"], "test discussion")
        self.assertIsNotNone(data["created"])
        self.assertIsNotNone(data["closed"])
        self.assertEqual(data["closed_by"]["id"], str(owner.id))
        self.assertEqual(len(data["discussion"]), 2)
        self.assertEqual(data["discussion"][1]["content"], "close bla bla")
        self.assertEqual(data["discussion"][1]["posted_by"]["id"], str(owner.id))
        self.assertIsNotNone(data["discussion"][1]["posted_on"])

        # Can't add anymore comments
        response = self.post(
            url_for("api.discussion", id=discussion.id), {"comment": "can't comment"}
        )
        self.assert403(response)

    def test_close_discussion_permissions(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        self.login()
        response = self.post(
            url_for("api.discussion", id=discussion.id), {"comment": "close bla bla", "close": True}
        )
        self.assert403(response)

        dataset.reload()
        # Metrics unchanged after attempt to close the discussion.
        self.assertEqual(dataset.get_metrics()["discussions"], 1)

    def test_delete_discussion(self):
        owner = self.login(AdminFactory())
        user = UserFactory()
        dataset = Dataset.objects.create(title="Test dataset", owner=owner)
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.
        self.assertEqual(Discussion.objects(subject=dataset).count(), 1)

        with assert_emit(on_discussion_deleted):
            response = self.delete(url_for("api.discussion", id=discussion.id))
        self.assertStatus(response, 204)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()["discussions"], 0)
        self.assertEqual(Discussion.objects(subject=dataset).count(), 0)

    def test_delete_discussion_comment(self):
        owner = self.login(AdminFactory())
        user = UserFactory()
        dataset = Dataset.objects.create(title="Test dataset", owner=owner)
        message = Message(content="bla bla", posted_by=user)
        message2 = Message(content="bla bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message, message2]
        )
        self.assertEqual(len(discussion.discussion), 2)

        # test first comment deletion
        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=0))
        self.assertStatus(response, 400)

        # test effective deletion
        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=1))
        self.assertStatus(response, 204)
        discussion.reload()
        self.assertEqual(len(discussion.discussion), 1)
        self.assertEqual(discussion.discussion[0].content, "bla bla")

        # delete again to test list overflow
        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=3))
        self.assertStatus(response, 404)

        # delete again to test last comment deletion
        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=0))
        self.assertStatus(response, 400)

    def test_delete_discussion_permissions(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        self.login()
        response = self.delete(url_for("api.discussion", id=discussion.id))
        self.assert403(response)

        dataset.reload()
        # Metrics unchanged after attempt to delete the discussion.
        self.assertEqual(dataset.get_metrics()["discussions"], 1)

    def test_delete_discussion_comment_permissions(self):
        dataset = Dataset.objects.create(title="Test dataset")
        user = UserFactory()
        message = Message(content="bla bla", posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset, user=user, title="test discussion", discussion=[message]
        )
        self.login()
        response = self.delete(url_for("api.discussion_comment", id=discussion.id, cidx=0))
        self.assert403(response)


class DiscussionsNotificationsTest(TestCase, DBTestMixin):
    def test_notify_user_discussions(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        open_discussions = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset, user=user, title=faker.sentence(), discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.utcnow(),
            closed_by=user,
        )

        notifications = discussions_notifications(owner)

        self.assertEqual(len(notifications), len(open_discussions))

        for dt, details in notifications:
            discussion = open_discussions[details["id"]]
            self.assertEqual(details["title"], discussion.title)
            self.assertEqual(details["subject"]["id"], discussion.subject.id)
            self.assertEqual(details["subject"]["type"], "dataset")

    def test_notify_org_discussions(self):
        recipient = UserFactory()
        member = Member(user=recipient, role="editor")
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(organization=org)

        open_discussions = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset, user=user, title=faker.sentence(), discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.utcnow(),
            closed_by=user,
        )

        notifications = discussions_notifications(recipient)

        self.assertEqual(len(notifications), len(open_discussions))

        for dt, details in notifications:
            discussion = open_discussions[details["id"]]
            self.assertEqual(details["title"], discussion.title)
            self.assertEqual(details["subject"]["id"], discussion.subject.id)
            self.assertEqual(details["subject"]["type"], "dataset")


class DiscussionsMailsTest(APITestCase):
    modules = []

    def test_new_discussion_mail(self):
        user = UserFactory()
        owner = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=user,
            title=faker.sentence(),
            discussion=[message],
        )

        with capture_mails() as mails:
            notify_new_discussion(discussion.id)

        # Should have sent one mail to the owner
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].recipients[0], owner.email)

    def test_new_discussion_comment_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        second_message = Message(content=faker.sentence(), posted_by=owner)
        new_message = Message(content=faker.sentence(), posted_by=commenter)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, second_message, new_message],
        )

        with capture_mails() as mails:
            notify_new_discussion_comment(discussion.id, message=len(discussion.discussion) - 1)

        # Should have sent one mail to the owner and the other participants
        # and no mail to the commenter. The owner should appear only once in the recipients
        # even if he is in both the discussion and the owner of the dataset.
        expected_recipients = (owner.email, poster.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(commenter.email, mail.recipients)

    def test_closed_discussion_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        second_message = Message(content=faker.sentence(), posted_by=commenter)
        closing_message = Message(content=faker.sentence(), posted_by=owner)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, second_message, closing_message],
        )

        with capture_mails() as mails:
            notify_discussion_closed(discussion.id, message=len(discussion.discussion) - 1)

        # Should have sent one mail to each participant
        # and no mail to the closer
        expected_recipients = (poster.email, commenter.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(owner.email, mail.recipients)
