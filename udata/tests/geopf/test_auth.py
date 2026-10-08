from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from authlib.oauth2.rfc6749 import OAuth2Token

from udata.core.user.factories import UserFactory
from udata.geopf.auth import resolve_access_token, revoke_token
from udata.geopf.client import GeopfReauthRequired
from udata.geopf.models import GeopfToken
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_GEOPF_CONF, create_geopf_token


@TEST_GEOPF_CONF
class ResolveAccessTokenTest(PytestOnlyDBTestCase):
    def test_no_stored_token_raises(self):
        user = UserFactory()
        with pytest.raises(GeopfReauthRequired):
            resolve_access_token(user=user)

    def test_returns_stored_token_when_valid(self):
        user = UserFactory()
        create_geopf_token(user, access_token="valid-access")

        assert resolve_access_token(user=user) == "valid-access"

    def test_refreshes_and_persists_when_expired(self):
        user = UserFactory()
        create_geopf_token(
            user,
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        new_token = OAuth2Token(
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            }
        )
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

    def test_keeps_old_refresh_token_when_response_omits_one(self):
        """A refresh response isn't required to include a new refresh_token (RFC 6749 §6)."""
        user = UserFactory()
        create_geopf_token(
            user,
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        new_token = OAuth2Token({"access_token": "new-access", "expires_in": 3600})
        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.return_value = new_token
            resolve_access_token(user=user)

        stored = GeopfToken.objects.get(user=user)
        assert stored.access_token == "new-access"
        assert stored.refresh_token == "old-refresh"

    def test_refreshes_when_expiring_within_min_validity(self):
        user = UserFactory()
        create_geopf_token(
            user,
            access_token="soon-stale",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        new_token = OAuth2Token(
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 43200,
            }
        )
        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.return_value = new_token
            result = resolve_access_token(user=user, min_validity=3600)

        assert result == "new-access"

    def test_no_refresh_when_valid_beyond_min_validity(self):
        user = UserFactory()
        create_geopf_token(
            user, access_token="still-good", expires_at=datetime.now(UTC) + timedelta(hours=2)
        )

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            assert resolve_access_token(user=user, min_validity=3600) == "still-good"
        mock_oauth.geopf.fetch_access_token.assert_not_called()

    def test_refresh_failure_raises_reauth_required(self):
        user = UserFactory()
        create_geopf_token(
            user,
            access_token="old-access",
            refresh_token="old-refresh",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.fetch_access_token.side_effect = Exception("boom")
            with pytest.raises(GeopfReauthRequired):
                resolve_access_token(user=user)


@TEST_GEOPF_CONF
class RevokeTokenTest(PytestOnlyDBTestCase):
    def test_posts_refresh_token_to_revocation_endpoint(self):
        user = UserFactory()
        geopf_token = create_geopf_token(user, refresh_token="the-refresh-token")

        with (
            patch("udata.geopf.auth.oauth") as mock_oauth,
            patch("udata.geopf.auth.requests.post") as mock_post,
        ):
            mock_oauth.geopf.load_server_metadata.return_value = {
                "revocation_endpoint": "https://sso.example.com/revoke"
            }
            mock_post.return_value = MagicMock(status_code=200)
            revoke_token(geopf_token)

        args, kwargs = mock_post.call_args
        assert args[0] == "https://sso.example.com/revoke"
        assert kwargs["data"]["token"] == "the-refresh-token"
        assert kwargs["data"]["token_type_hint"] == "refresh_token"

    def test_does_not_raise_when_no_revocation_endpoint(self):
        user = UserFactory()
        geopf_token = create_geopf_token(user)

        with patch("udata.geopf.auth.oauth") as mock_oauth:
            mock_oauth.geopf.load_server_metadata.return_value = {}
            revoke_token(geopf_token)  # must not raise

    def test_does_not_raise_when_revocation_call_fails(self):
        user = UserFactory()
        geopf_token = create_geopf_token(user)

        with (
            patch("udata.geopf.auth.oauth") as mock_oauth,
            patch("udata.geopf.auth.requests.post") as mock_post,
        ):
            mock_oauth.geopf.load_server_metadata.return_value = {
                "revocation_endpoint": "https://sso.example.com/revoke"
            }
            mock_post.side_effect = Exception("network error")
            revoke_token(geopf_token)  # must not raise
