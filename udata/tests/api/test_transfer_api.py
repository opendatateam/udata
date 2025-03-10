from bson import ObjectId
from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
from udata.utils import faker

from . import APITestCase


class TransferAPITest(APITestCase):
    modules = []

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
