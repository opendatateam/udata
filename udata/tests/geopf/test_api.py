from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import redirect, url_for

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.user.factories import UserFactory
from udata.geopf.api import DATASET_SESSION_KEY
from udata.geopf.models import GeopfToken
from udata.tests.api import APITestCase
from udata.tests.geopf import TEST_API_BASE, TEST_GEOPF_CONF

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
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        GeopfToken(user=user, access_token="a", refresh_token="r", expires_at=expires_at).save()

        response = self.get(url_for("api.geopf_status"))
        self.assert200(response)
        assert response.json["connected"] is True

    def test_connected_refreshes_and_reports_new_expiry_when_access_token_stale(self):
        user = self.login()
        GeopfToken(
            user=user,
            access_token="stale",
            refresh_token="still-good",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        ).save()
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
        GeopfToken(
            user=user,
            access_token="stale",
            refresh_token="dead",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        ).save()

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.side_effect = Exception("invalid_grant")
            response = self.get(url_for("api.geopf_status"))

        self.assert200(response)
        assert response.json == {"connected": False, "expires_at": None}


@TEST_GEOPF_CONF
class GeopfTokenApiTest(APITestCase):
    def test_disconnect_revokes_refresh_token_at_idp(self):
        user = self.login()
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="the-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        with (
            patch("udata.geopf.auth.oauth") as mock_oauth,
            patch("udata.geopf.auth.requests.post") as mock_post,
        ):
            mock_oauth.geopf.load_server_metadata.return_value = {
                "revocation_endpoint": "https://sso.example.com/revoke"
            }
            mock_post.return_value = MagicMock(status_code=200)
            response = self.delete(url_for("api.geopf_token"))

        self.assert204(response)
        assert GeopfToken.objects(user=user.id).first() is None
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://sso.example.com/revoke"
        assert kwargs["data"]["token"] == "the-refresh-token"

    def test_disconnect_succeeds_even_if_revocation_fails(self):
        user = self.login()
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.load_server_metadata.side_effect = Exception("unreachable")
            response = self.delete(url_for("api.geopf_token"))

        self.assert204(response)
        assert GeopfToken.objects(user=user.id).first() is None

    def test_disconnect_with_no_stored_token_is_a_noop(self):
        self.login()
        response = self.delete(url_for("api.geopf_token"))
        self.assert204(response)


@TEST_GEOPF_CONF
class GeopfDatastoresApiTest(APITestCase):
    def test_not_connected_returns_409(self):
        self.login()
        response = self.get(url_for("api.geopf_datastores"))
        self.assertStatus(response, 409)

    def test_connected_lists_datastores(self):
        user = self.login()
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

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
            owner=user, resources=[resource], extras={"geopf:push:datastore-id": "ds-existing"}
        )
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        self.assertStatus(response, 202)

    def test_not_connected_returns_409(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(owner=user, resources=[resource])

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assertStatus(response, 409)

    def test_connected_enqueues_push_task(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            owner=user, resources=[resource], extras={"geopf:push:datastore-id": "ds-existing"}
        )
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

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
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

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
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))
        self.assert400(response)

    def test_pinned_datastore_satisfies_check(self):
        user = self.login()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            owner=user,
            resources=[resource],
            extras={"geopf:push:datastore-id": "ds-pinned"},
        )
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        with patch("udata.geopf.api.push_resource_to_geopf.delay", return_value=MagicMock(id="t")):
            response = self.post(url_for("api.geopf_push", dataset=dataset, rid=resource.id))

        self.assertStatus(response, 202)


@TEST_GEOPF_CONF
class GeopfPullOfferingsApiTest(APITestCase):
    def test_requires_edit_permission(self):
        owner = UserFactory()
        self.login()  # a different user, no rights on the dataset
        dataset = DatasetFactory(owner=owner)

        response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))
        self.assert403(response)

    def test_not_connected_returns_409(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))
        self.assertStatus(response, 409)

    def test_connected_enqueues_sync_task(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        mock_task = MagicMock(id="task-456")
        with patch(
            "udata.geopf.api.pull_offerings_from_geopf.delay", return_value=mock_task
        ) as mock_delay:
            response = self.post(url_for("api.geopf_pull_offerings", dataset=dataset))

        self.assertStatus(response, 202)
        assert response.json == {"task_id": "task-456"}
        mock_delay.assert_called_once_with(str(dataset.id), str(user.id))
