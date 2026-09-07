from bson import ObjectId
from flask import url_for

from udata.core.dataset.factories import DatasetFactory, LicenseFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.topic.factories import TopicFactory
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
from udata.utils import faker

from . import APITestCase


class TransferAPITest(APITestCase):
    def test_request_dataset_transfer(self):
        user = self.login()
        recipient_user = UserFactory()
        recipient_org = OrganizationFactory()
        dataset = DatasetFactory(owner=user)
        comment = faker.sentence()

        # It's a little bit weird to create two transfer for the same dataset
        # but it's currently allowed. If we change this, we can create a second
        # dataset for this test.

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(dataset.id),
                },
                "recipient": {
                    "class": "Organization",
                    "id": str(recipient_org.id),
                },
                "comment": comment,
            },
        )
        self.assert201(response)

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(dataset.id),
                },
                "recipient": {
                    "class": "User",
                    "id": str(recipient_user.id),
                },
                "comment": comment,
            },
        )

        self.assert201(response)

        data = response.json

        self.assertEqual(data["user"]["id"], str(user.id))

        self.assertEqual(data["recipient"]["id"], str(recipient_user.id))
        self.assertEqual(data["recipient"]["class"], "User")

        self.assertEqual(data["subject"]["id"], str(dataset.id))
        self.assertEqual(data["subject"]["class"], "Dataset")

        self.assertEqual(data["owner"]["id"], str(user.id))
        self.assertEqual(data["owner"]["class"], "User")

        self.assertEqual(data["comment"], comment)
        self.assertEqual(data["status"], "pending")

        response = self.get(
            url_for(
                "api.transfers",
                subject=str(dataset.id),
            ),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 2)

        self.assertEqual(data[0]["recipient"]["id"], str(recipient_org.id))
        self.assertEqual(data[0]["recipient"]["class"], "Organization")

        self.assertEqual(data[0]["subject"]["id"], str(dataset.id))
        self.assertEqual(data[0]["subject"]["class"], "Dataset")

        self.assertEqual(data[0]["owner"]["id"], str(user.id))
        self.assertEqual(data[0]["owner"]["class"], "User")

        self.assertEqual(data[0]["comment"], comment)
        self.assertEqual(data[0]["status"], "pending")

        self.assertEqual(data[1]["recipient"]["id"], str(recipient_user.id))
        self.assertEqual(data[1]["recipient"]["class"], "User")

        self.assertEqual(data[1]["subject"]["id"], str(dataset.id))
        self.assertEqual(data[1]["subject"]["class"], "Dataset")

        self.assertEqual(data[1]["owner"]["id"], str(user.id))
        self.assertEqual(data[1]["owner"]["class"], "User")

        self.assertEqual(data[1]["comment"], comment)
        self.assertEqual(data[1]["status"], "pending")

        response = self.get(
            url_for(
                "api.transfers",
                subject_type="Reuse",
                recipient=str(recipient_user.id),
            ),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 0)

        response = self.get(
            url_for(
                "api.transfers",
                subject_type="Dataset",
                recipient=str(recipient_user.id),
            ),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 1)

        response = self.get(
            url_for(
                "api.transfers",
                recipient=str(recipient_user.id),
            ),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 1)

        self.login(recipient_user)

        response = self.get(
            url_for("api.transfers", recipient=recipient_user.id),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 1)

        # New login
        self.login()

        response = self.get(
            url_for("api.transfers", recipient=recipient_user.id),
        )
        self.assert200(response)

        data = response.json
        self.assertEqual(len(data), 0)

    def test_400_on_malformed_subject_filter(self):
        self.login()

        response = self.get(url_for("api.transfers", subject="not-an-object-id"))

        self.assert400(response)
        self.assertIn("`subject`", response.json["message"])

    def test_400_on_malformed_recipient_filter(self):
        self.login()

        response = self.get(url_for("api.transfers", recipient="not-an-object-id"))

        self.assert400(response)
        self.assertIn("`recipient`", response.json["message"])

    def test_400_on_bad_subject(self):
        self.login()
        recipient = UserFactory()
        comment = faker.sentence()

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(ObjectId()),
                },
                "recipient": {
                    "class": "User",
                    "id": str(recipient.id),
                },
                "comment": comment,
            },
        )

        self.assert400(response)

        data = response.json

        self.assertIn("subject", data["errors"])

    def test_400_on_bad_recipient(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        comment = faker.sentence()

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(dataset.id),
                },
                "recipient": {
                    "class": "User",
                    "id": str(ObjectId()),
                },
                "comment": comment,
            },
        )

        self.assert400(response)

        data = response.json

        self.assertIn("recipient", data["errors"])

    def test_400_on_subject_class_outside_transferable_types(self):
        """`db.resolve_model` resolves any registered document, a `License` included."""
        self.login()
        recipient = UserFactory()
        LicenseFactory(id="other-at")
        LicenseFactory(id="other-open")

        response = self.post(
            url_for("api.transfers"),
            {
                # A `StringField` primary key lets the operators through untouched, so
                # this used to query the licenses and blow up on the second match.
                "subject": {"class": "License", "id": {"$regex": "^other-"}},
                "recipient": {"class": "User", "id": str(recipient.id)},
                "comment": faker.sentence(),
            },
        )

        self.assert400(response)
        self.assertIn("subject", response.json["errors"])

    def test_400_on_subject_class_that_resolves_to_a_single_document(self):
        """Same hole as above, one step further: the lookup succeeds and the crash moves.

        With an id matching exactly one licence, `objects.get()` returns it and the
        request reaches `TransferPermission`, which reads `subject.organization` — an
        attribute a `License` simply does not have. Rejecting the class is the only thing
        that covers this: a licence is not an `Owned`, so no amount of care inside the
        permission would help.
        """
        self.login()
        recipient = UserFactory()
        license = LicenseFactory()

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {"class": "License", "id": license.id},
                "recipient": {"class": "User", "id": str(recipient.id)},
                "comment": faker.sentence(),
            },
        )

        self.assert400(response)
        self.assertIn("subject", response.json["errors"])

    def test_403_on_a_subject_nobody_owns(self):
        """Purging an organization leaves its datasets behind with no owner at all.

        Such a dataset is a perfectly regular `Dataset`, so it goes through the class and
        id checks untouched and reaches the permission, which finds nobody entitled to
        give it away. That has to be a refusal, not a crash.
        """
        self.login()
        orphan = DatasetFactory()
        self.assertIsNone(orphan.owner)
        self.assertIsNone(orphan.organization)

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {"class": "Dataset", "id": str(orphan.id)},
                "recipient": {"class": "User", "id": str(UserFactory().id)},
                "comment": faker.sentence(),
            },
        )

        self.assert403(response)

    def test_request_topic_transfer(self):
        """Topics are owned like datasets, and transferring one is supported."""
        user = self.login()
        recipient_org = OrganizationFactory()
        topic = TopicFactory(owner=user)

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {"class": "Topic", "id": str(topic.id)},
                "recipient": {"class": "Organization", "id": str(recipient_org.id)},
                "comment": faker.sentence(),
            },
        )
        self.assert201(response)
        self.assertEqual(response.json["subject"]["class"], "Topic")
        self.assertEqual(response.json["subject"]["id"], str(topic.id))

        # The listing marshals the subject with a `Polymorph`, which raises on a class it
        # does not know about — so reading the transfer back is a distinct guarantee.
        response = self.get(url_for("api.transfers", subject=str(topic.id)))
        self.assert200(response)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["subject"]["name"], topic.name)
        self.assertEqual(response.json[0]["subject"]["page"], topic.self_web_url())

    def test_400_on_recipient_class_outside_persons(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {"class": "Dataset", "id": str(dataset.id)},
                "recipient": {"class": "Dataset", "id": str(dataset.id)},
                "comment": faker.sentence(),
            },
        )

        self.assert400(response)
        self.assertIn("recipient", response.json["errors"])

    def test_400_on_mongo_operators_as_subject_id(self):
        user = self.login()
        DatasetFactory(owner=user)
        recipient = UserFactory()

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {"class": "Dataset", "id": {"$ne": None}},
                "recipient": {"class": "User", "id": str(recipient.id)},
                "comment": faker.sentence(),
            },
        )

        self.assert400(response)
        self.assertIn("subject", response.json["errors"])

    def test_400_on_malformed_subject_reference(self):
        self.login()
        recipient = UserFactory()

        for subject in ("Dataset", {"class": "Dataset"}, {"class": "Dataset", "id": "not-an-id"}):
            response = self.post(
                url_for("api.transfers"),
                {
                    "subject": subject,
                    "recipient": {"class": "User", "id": str(recipient.id)},
                    "comment": faker.sentence(),
                },
            )

            self.assert400(response)
            self.assertIn("subject", response.json["errors"])

    def test_cannot_accept_or_refuse_transfer_after_accepting_or_refusing(self):
        user = self.login()
        new_user = UserFactory()
        dataset = DatasetFactory(owner=user)

        response = self._create_transfer(dataset, new_user)
        self.assert201(response)

        transfer = response.json

        self.login(new_user)
        response = self.post(url_for("api.transfer", id=transfer["id"]), {"response": "accept"})
        self.assert200(response)

        response = self.post(url_for("api.transfer", id=transfer["id"]), {"response": "accept"})
        self.assert400(response)

        response = self.post(url_for("api.transfer", id=transfer["id"]), {"response": "refuse"})
        self.assert400(response)

    def _create_transfer(self, source: Dataset, destination: User):
        return self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(source.id),
                },
                "recipient": {
                    "class": "User",
                    "id": str(destination.id),
                },
                "comment": "Some comment",
            },
        )
