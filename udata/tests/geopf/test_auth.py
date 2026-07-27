from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from udata.core.user.factories import UserFactory
from udata.geopf.auth import resolve_access_token
from udata.geopf.client import GeopfReauthRequired
from udata.geopf.models import GeopfToken
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_GEOPF_CONF


@TEST_GEOPF_CONF
class ResolveAccessTokenTest(PytestOnlyDBTestCase):
    def test_raw_token_bypasses_storage(self):
        assert resolve_access_token(raw_token="raw-token") == "raw-token"

    def test_no_user_and_no_raw_token_raises(self):
        with pytest.raises(GeopfReauthRequired):
            resolve_access_token()

    def test_no_stored_token_raises(self):
        user = UserFactory()
        with pytest.raises(GeopfReauthRequired):
            resolve_access_token(user=user)

    def test_returns_stored_token_when_valid(self):
        user = UserFactory()
        GeopfToken(
            user=user,
            access_token="valid-access",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        assert resolve_access_token(user=user) == "valid-access"

    def test_refreshes_and_persists_when_expired(self):
        user = UserFactory()
        GeopfToken(
            user=user,
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ).save()

        new_token = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.return_value = new_token
            result = resolve_access_token(user=user)

        assert result == "new-access"
        mock_oauth.geopf.fetch_access_token.assert_called_once_with(
            grant_type="refresh_token", refresh_token="old-refresh"
        )
        stored = GeopfToken.objects.get(user=user)
        assert stored.access_token == "new-access"
        assert stored.refresh_token == "new-refresh"

    def test_refresh_failure_raises_reauth_required(self):
        user = UserFactory()
        GeopfToken(
            user=user,
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ).save()

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.side_effect = Exception("boom")
            with pytest.raises(GeopfReauthRequired):
                resolve_access_token(user=user)
