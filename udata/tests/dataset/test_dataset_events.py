from unittest.mock import patch

import pytest
from flask import current_app
from requests.compat import json as complexjson

from udata.core.dataset.events import serialize_resource_for_event
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Schema
from udata.models import Dataset
from udata.tests.helpers import assert_emit


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("enable_resource_event")
class DatasetEventsTest:
    @patch("requests.post")
    @pytest.mark.options(RESOURCES_ANALYSER_API_KEY=None)
    def test_publish_message_resource_created_no_api_key(self, mock_req):
        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        expected_value = {
            "resource_id": str(resource.id),
            "dataset_id": str(dataset.id),
            "document": serialize_resource_for_event(resource),
        }

        mock_req.assert_called_with(
            f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/created/",
            json=expected_value,
            headers={},  # No RESOURCES_ANALYSER_API_KEY, no headers.
        )

    @patch("requests.post")
    @pytest.mark.options(RESOURCES_ANALYSER_API_KEY="foobar-api-key")
    def test_publish_message_resource_created(self, mock_req):
        dataset = DatasetFactory()
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        expected_value = {
            "resource_id": str(resource.id),
            "dataset_id": str(dataset.id),
            "document": serialize_resource_for_event(resource),
        }

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)

        mock_req.assert_called_with(
            f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/created/",
            json=expected_value,
            headers={"Authorization": "Bearer foobar-api-key"},
        )

    @patch("requests.post")
    @pytest.mark.options(RESOURCES_ANALYSER_API_KEY="foobar-api-key")
    def test_publish_message_resource_modified(self, mock_req):
        resource = ResourceFactory(schema=Schema(url="http://localhost/my-schema"))
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = "New description"

        expected_value = {
            "resource_id": str(resource.id),
            "dataset_id": str(dataset.id),
            "document": serialize_resource_for_event(resource),
        }

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)

        mock_req.assert_called_with(
            f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/updated/",
            json=expected_value,
            headers={"Authorization": "Bearer foobar-api-key"},
        )

        # Mocking requests call doesn't call the JSON encoder
        # so calling it manually here to prevent encoding errors.
        # (for example, encoding Embeds fails)
        complexjson.dumps(expected_value)

    @patch("requests.post")
    @pytest.mark.options(RESOURCES_ANALYSER_API_KEY="foobar-api-key")
    def test_publish_message_resource_removed(self, mock_req):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        expected_signals = (Dataset.on_resource_removed,)

        expected_value = {
            "resource_id": str(resource.id),
            "dataset_id": str(dataset.id),
            "document": None,
        }

        with assert_emit(*expected_signals):
            dataset.remove_resource(resource)

        mock_req.assert_called_with(
            f"{current_app.config['RESOURCES_ANALYSER_URI']}/api/resource/deleted/",
            json=expected_value,
            headers={"Authorization": "Bearer foobar-api-key"},
        )
