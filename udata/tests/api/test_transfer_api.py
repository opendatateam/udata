from bson import ObjectId
from flask import url_for
from mock import patch

from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import UserFactory
from udata.features.transfer.factories import TransferFactory
from udata.utils import faker

from . import APITestCase


class TransferAPITest(APITestCase):
    modules = []

    @patch("udata.features.transfer.api.request_transfer")
    def test_request_dataset_transfer(self, action):
        user = self.login()
        recipient = UserFactory()
        dataset = DatasetFactory(owner=user)
        comment = faker.sentence()

        action.return_value = TransferFactory(
            owner=user, recipient=recipient, subject=dataset, comment=comment
        )

        response = self.post(
            url_for("api.transfers"),
            {
                "subject": {
                    "class": "Dataset",
                    "id": str(dataset.id),
                },
                "recipient": {
                    "class": "User",
                    "id": str(recipient.id),
                },
                "comment": comment,
            },
        )

        self.assert201(response)

        action.assert_called_with(dataset, recipient, comment)

        data = response.json

        self.assertEqual(data["recipient"]["id"], str(recipient.id))
        self.assertEqual(data["recipient"]["class"], "User")

        self.assertEqual(data["subject"]["id"], str(dataset.id))
        self.assertEqual(data["subject"]["class"], "Dataset")

        self.assertEqual(data["owner"]["id"], str(user.id))
        self.assertEqual(data["owner"]["class"], "User")

        self.assertEqual(data["comment"], comment)
        self.assertEqual(data["status"], "pending")

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
