from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import redirect, url_for

from udata.core.dataset.factories import (
    DatasetFactory,
    HiddenDatasetFactory,
    ResourceFactory,
)
from udata.core.user.factories import UserFactory
from udata.geopf.api import DATASET_SESSION_KEY
from udata.geopf.models import (
    GeopfDatasetMetadata,
    GeopfDatasetPullMetadata,
    GeopfDatasetPushMetadata,
    GeopfResourceMetadata,
    GeopfResourceOfferingMetadata,
    GeopfResourcePushMetadata,
    GeopfToken,
)
from udata.tests.api import APITestCase
from udata.tests.geopf import TEST_API_BASE, TEST_GEOPF_CONF, create_geopf_token

CDATA_BASE_URL = "https://cdata.example.com"


@TEST_GEOPF_CONF
class GeopfLoginApiTest(APITestCase):
    def test_requires_login(self):
        response = self.get(url_for("api.geopf_login"))
        self.assert401(response)

    def test_redirects_to_provider_and_stores_dataset_id(self):
        self.login()
        dataset = DatasetFactory()
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_redirect.return_value = redirect(TEST_API_BASE)
            response = self.get(url_for("api.geopf_login", dataset_id=str(dataset.id)))

        self.assertEqual(response.status_code, 302)
        mock_oauth.geopf.authorize_redirect.assert_called_once()
        with self.client.session_transaction() as sess:
            assert sess[DATASET_SESSION_KEY] == str(dataset.id)

    def test_stores_none_when_no_dataset_id_given(self):
        self.login()
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_redirect.return_value = redirect(TEST_API_BASE)
            self.get(url_for("api.geopf_login"))

        with self.client.session_transaction() as sess:
            assert sess[DATASET_SESSION_KEY] is None


@pytest.mark.options(CDATA_BASE_URL=CDATA_BASE_URL)
@TEST_GEOPF_CONF
class GeopfAuthApiTest(APITestCase):
    def test_stores_token_and_redirects_to_dataset_page(self):
        user = self.login()
        dataset = DatasetFactory()
        with self.client.session_transaction() as sess:
            sess[DATASET_SESSION_KEY] = str(dataset.id)

        token = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_access_token.return_value = token
            response = self.get(url_for("api.geopf_auth"))

        self.assertEqual(response.status_code, 302)
        assert response.location.startswith(f"{CDATA_BASE_URL}/admin/datasets/{dataset.id}/geopf")
        stored = GeopfToken.objects.get(user=user.id)
        assert stored.access_token == "at"
        assert stored.refresh_token == "rt"

    def test_redirects_home_when_no_dataset_id_stored(self):
        self.login()
        token = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_access_token.return_value = token
            response = self.get(url_for("api.geopf_auth"))

        self.assertEqual(response.status_code, 302)
        assert response.location.startswith(CDATA_BASE_URL)

    def test_redirects_home_when_dataset_id_unknown(self):
        self.login()
        with self.client.session_transaction() as sess:
            sess[DATASET_SESSION_KEY] = "000000000000000000000000"

        token = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_access_token.return_value = token
            response = self.get(url_for("api.geopf_auth"))

        self.assertEqual(response.status_code, 302)
        assert "/datasets/" not in response.location

    def test_redirects_home_when_dataset_id_malformed(self):
        """A malformed id (not a valid ObjectId) must fall back safely, not error out."""
        self.login()
        with self.client.session_transaction() as sess:
            sess[DATASET_SESSION_KEY] = "not-an-id"

        token = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        with patch("udata.geopf.api.oauth") as mock_oauth:
            mock_oauth.geopf.authorize_access_token.return_value = token
            response = self.get(url_for("api.geopf_auth"))

        self.assertEqual(response.status_code, 302)
        assert "/datasets/" not in response.location


@TEST_GEOPF_CONF
class GeopfStatusApiTest(APITestCase):
    def test_not_connected(self):
        self.login()
        response = self.get(url_for("api.geopf_status"))
        self.assert200(response)
        assert response.json == {"connected": False, "expires_at": None}

    def test_connected(self):
        user = self.login()
        create_geopf_token(user)

        response = self.get(url_for("api.geopf_status"))
        self.assert200(response)
        assert response.json["connected"] is True

    def test_connected_refreshes_and_reports_new_expiry_when_access_token_stale(self):
        user = self.login()
        create_geopf_token(
            user,
            access_token="stale",
            refresh_token="still-good",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        new_token = {
            "access_token": "fresh",
            "refresh_token": "fresh-refresh",
            "expires_in": 3600,
        }
        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.return_value = new_token
            response = self.get(url_for("api.geopf_status"))

        self.assert200(response)
        assert response.json["connected"] is True
        assert GeopfToken.objects.get(user=user).access_token == "fresh"

    def test_not_connected_when_refresh_token_is_also_dead(self):
        user = self.login()
        create_geopf_token(
            user,
            access_token="stale",
            refresh_token="dead",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.side_effect = Exception("invalid_grant")
            response = self.get(url_for("api.geopf_status"))

        self.assert200(response)
        assert response.json == {"connected": False, "expires_at": None}


@TEST_GEOPF_CONF
class GeopfTokenApiTest(APITestCase):
    def test_disconnect_revokes_refresh_token_at_idp(self):
        user = self.login()
        token = create_geopf_token(user, refresh_token="the-refresh-token")

        with patch("udata.geopf.api.revoke_token") as mock_revoke:
            response = self.delete(url_for("api.geopf_token"))

        self.assert204(response)
        assert GeopfToken.objects(user=user.id).first() is None
        mock_revoke.assert_called_once_with(token)

    def test_disconnect_with_no_stored_token_is_a_noop(self):
        self.login()
        response = self.delete(url_for("api.geopf_token"))
        self.assert204(response)


@TEST_GEOPF_CONF
class GeopfDatastoresApiTest(APITestCase):
    def test_not_connected_returns_424(self):
        self.login()
        response = self.get(url_for("api.geopf_datastores"))
        self.assertStatus(response, 424)

    def test_connected_lists_datastores(self):
        user = self.login()
        create_geopf_token(user)

        datastores = [{"datastore_id": "ds-1", "name": "my-entrepot", "rights": ["UPLOAD"]}]
        with patch("udata.geopf.api.GeopfClient") as mock_client_cls:
            mock_client_cls.return_value.list_datastores.return_value = datastores
            response = self.get(url_for("api.geopf_datastores"))

        self.assert200(response)
        assert response.json == datastores


@TEST_GEOPF_CONF
class GeopfPushApiTest(APITestCase):
    def test_requires_edit_permission(self):
        owner = UserFactory()
        self.login()  # a different user, no rights on the dataset
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=owner, resources=[resource])

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assert403(response)

    def test_resource_not_found(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.post(
            url_for("api.geopf_push", dataset=dataset, rid="00000000-0000-0000-0000-000000000000")
        )
        self.assert404(response)

    def test_rejects_non_gpkg_resource(self):
        user = self.login()
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assert400(response)

    @pytest.mark.options(GEOPF_PUSHABLE_FORMATS=frozenset({"gpkg", "csv"}))
    def test_allows_format_permitted_by_config(self):
        user = self.login()
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-existing")),
        )
        create_geopf_token(user)

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        self.assertStatus(response, 202)

    def test_not_connected_returns_424(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assertStatus(response, 424)

    def test_connected_enqueues_push_task(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-existing")),
        )
        create_geopf_token(user)

        mock_task = MagicMock(id="task-123")
        with patch(
            "udata.geopf.api.push_resource_to_geopf.delay", return_value=mock_task
        ) as mock_delay:
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        self.assertStatus(response, 202)
        assert response.json == {"task_id": "task-123"}
        mock_delay.assert_called_once_with(str(dataset.id), str(resource.id), str(user.id), None)

    def test_passes_through_requested_datastore_id(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])
        create_geopf_token(user)

        mock_task = MagicMock(id="task-123")
        with patch(
            "udata.geopf.api.push_resource_to_geopf.delay", return_value=mock_task
        ) as mock_delay:
            response = self.post(
                url_for("api.geopf_push", dataset=dataset, rid=resource.id),
                data={"datastore_id": "ds-chosen"},
            )

        self.assertStatus(response, 202)
        mock_delay.assert_called_once_with(
            str(dataset.id), str(resource.id), str(user.id), "ds-chosen"
        )

    def test_no_resolvable_datastore_returns_400(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])
        create_geopf_token(user)

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assert400(response)

    def test_pinned_datastore_satisfies_check(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-pinned")),
        )
        create_geopf_token(user)

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        self.assertStatus(response, 202)

    def test_marks_resource_pending_before_the_worker_runs(self):
        """The status route must report `pending` as soon as the request is accepted."""
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-existing")),
        )
        create_geopf_token(user)

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assertStatus(response, 202)

        status = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(status)
        assert status.json["pushable"][0]["push"]["status"] == "pending"
        assert status.json["pushable"][0]["push"]["task_id"] == "t"

    def test_clears_the_previous_runs_error(self):
        user = self.login()
        resource = ResourceFactory.build(
            format="gpkg",
            url="http://files.example.com/f.gpkg",
            geopf=GeopfResourceMetadata(
                push=GeopfResourcePushMetadata(status="error", error="previously boom")
            ),
        )
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-existing")),
        )
        create_geopf_token(user)

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        status = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        assert status.json["pushable"][0]["push"]["error"] is None


@TEST_GEOPF_CONF
class GeopfPullOfferingsApiTest(APITestCase):
    def test_requires_edit_permission(self):
        owner = UserFactory()
        self.login()  # a different user, no rights on the dataset
        dataset = DatasetFactory(owner=owner)

        response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))
        self.assert403(response)

    def test_not_connected_returns_424(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))
        self.assertStatus(response, 424)

    def test_connected_enqueues_sync_task(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        create_geopf_token(user)

        mock_task = MagicMock(id="task-456")
        with patch(
            "udata.geopf.api.pull_offerings_from_geopf.delay", return_value=mock_task
        ) as mock_delay:
            response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))

        self.assertStatus(response, 202)
        assert response.json == {"task_id": "task-456"}
        mock_delay.assert_called_once_with(str(dataset.id), str(user.id))

    def test_marks_dataset_pending_before_the_worker_runs(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        create_geopf_token(user)

        with patch(
            "udata.geopf.api.pull_offerings_from_geopf.delay", return_value=MagicMock(id="t")
        ):
            response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))
        self.assertStatus(response, 202)

        status = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(status)
        assert status.json["pull"]["status"] == "pending"
        assert status.json["pull"]["task_id"] == "t"

    def test_clears_the_previous_runs_error(self):
        user = self.login()
        dataset = DatasetFactory(
            owner=user,
            geopf=GeopfDatasetMetadata(
                pull=GeopfDatasetPullMetadata(status="error", error="previously boom")
            ),
        )
        create_geopf_token(user)

        with patch(
            "udata.geopf.api.pull_offerings_from_geopf.delay", return_value=MagicMock(id="t")
        ):
            self.post(url_for("api.geopf_pull_offerings", dataset=dataset))

        status = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        assert status.json["pull"]["error"] is None


@TEST_GEOPF_CONF
class GeopfDatasetStatusApiTest(APITestCase):
    def test_requires_login(self):
        dataset = DatasetFactory()
        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert401(response)

    def test_readable_without_edit_permission(self):
        """Every value here is public through the apiv2 extras endpoints anyway."""
        owner = UserFactory()
        self.login()  # a different user, no rights on the dataset
        dataset = DatasetFactory(owner=owner)

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)

    def test_hidden_dataset_requires_read_permission(self):
        owner = UserFactory()
        self.login()  # a different user, no rights on the dataset
        dataset = HiddenDatasetFactory(owner=owner)

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert403(response)

    def test_empty_dataset(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json == {
            "push": {
                "datastore_id": None,
                "fiche_url": None,
            },
            "pull": {
                "status": None,
                "last_synced_at": None,
                "error": None,
                "task_id": None,
            },
            "pushable": [],
            "offerings": [],
        }

    def test_never_pushed_resource(self):
        """A pushable resource with no geopf metadata yet reports every push field as null."""
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json["pushable"] == [
            {
                "id": str(resource.id),
                "title": resource.title,
                "format": "gpkg",
                "url": "http://files.example.com/f.gpkg",
                "push": {
                    "status": None,
                    "last_synced_at": None,
                    "error": None,
                    "task_id": None,
                    "stored_data_id": None,
                },
            }
        ]

    def test_pushed_resource(self):
        user = self.login()
        resource = ResourceFactory.build(
            format="gpkg",
            url="http://files.example.com/f.gpkg",
            geopf=GeopfResourceMetadata(
                push=GeopfResourcePushMetadata(
                    status="done",
                    last_synced_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
                    task_id="task-1",
                    stored_data_id="sd-1",
                )
            ),
        )
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            geopf=GeopfDatasetMetadata(
                push=GeopfDatasetPushMetadata(
                    datastore_id="ds-1", fiche_url="https://cartes.example.com/fiche"
                ),
                pull=GeopfDatasetPullMetadata(status="error", error="boom", task_id="task-2"),
            ),
        )

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json["push"] == {
            "datastore_id": "ds-1",
            "fiche_url": "https://cartes.example.com/fiche",
        }
        assert response.json["pull"] == {
            "status": "error",
            "last_synced_at": None,
            "error": "boom",
            "task_id": "task-2",
        }
        assert response.json["pushable"][0]["push"] == {
            "status": "done",
            "last_synced_at": "2026-01-02T03:04:05+00:00",
            "error": None,
            "task_id": "task-1",
            "stored_data_id": "sd-1",
        }

    def test_offering_resource(self):
        user = self.login()
        resource = ResourceFactory.build(
            title="Service WFS - communes",
            format="wfs",
            url="http://data.example.com/wfs",
            geopf=GeopfResourceMetadata(
                offering=GeopfResourceOfferingMetadata(
                    id="off-1", last_synced_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
                )
            ),
        )
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json["pushable"] == []
        assert response.json["offerings"] == [
            {
                "id": str(resource.id),
                "title": "Service WFS - communes",
                "format": "wfs",
                "url": "http://data.example.com/wfs",
                "offering": {"id": "off-1", "last_synced_at": "2026-01-02T03:04:05+00:00"},
            }
        ]

    @pytest.mark.options(GEOPF_PUSHABLE_FORMATS=frozenset({"gpkg", "wfs"}))
    def test_offering_never_listed_as_pushable(self):
        """Offerings stay out of `pushable` even when their format is configured pushable."""
        user = self.login()
        resource = ResourceFactory.build(
            format="wfs",
            geopf=GeopfResourceMetadata(offering=GeopfResourceOfferingMetadata(id="off-1")),
        )
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json["pushable"] == []
        assert len(response.json["offerings"]) == 1

    def test_non_pushable_format_excluded(self):
        user = self.login()
        csv_resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        no_format = ResourceFactory.build(format=None, url="http://files.example.com/f")
        dataset = DatasetFactory(owner=user, resources=[csv_resource, no_format])

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert response.json["pushable"] == []
        assert response.json["offerings"] == []

    @pytest.mark.options(GEOPF_PUSHABLE_FORMATS=frozenset({"gpkg", "csv"}))
    def test_respects_configured_formats(self):
        user = self.login()
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert [r["id"] for r in response.json["pushable"]] == [str(resource.id)]

    def test_works_when_not_connected(self):
        """Unlike push/pull, this route reports local state without a geopf link."""
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])
        assert GeopfToken.objects(user=user.id).first() is None

        response = self.get(url_for("api.geopf_dataset_status", dataset=dataset))
        self.assert200(response)
        assert len(response.json["pushable"]) == 1
