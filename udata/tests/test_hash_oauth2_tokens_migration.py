from flask import url_for
from mongoengine.connection import get_db

from udata.api.factories import CLIENT_SECRET, OAuth2ClientFactory, OAuth2TokenFactory
from udata.api.oauth2 import OAuth2Token
from udata.core.api_token.hashing import hash_token
from udata.db import migrations
from udata.tests.api import PytestOnlyAPITestCase, basic_header
from udata.tests.helpers import assert200

MIGRATION = "2026-11-11-hash-oauth2-tokens.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class HashOAuth2TokensMigrationTest(PytestOnlyAPITestCase):
    """The factories store hashes: a value in clear is set on the stored field itself."""

    def test_tokens_in_clear_are_hashed_and_keep_authenticating(self):
        token = OAuth2TokenFactory(access_token="access-token", refresh_token="refresh-token")

        migrate()

        token.reload()
        assert token.refresh_token == hash_token("refresh-token")
        response = self.get(url_for("api.me"), headers={"Authorization": "Bearer access-token"})
        assert200(response)
        assert response.json["id"] == str(token.user.id)

    def test_a_token_without_refresh_token_keeps_none(self):
        token = OAuth2TokenFactory(access_token="access-token", refresh_token=None)

        migrate()

        raw = OAuth2Token._get_collection().find_one({"_id": token.id})
        assert raw["access_token"] == hash_token("access-token")
        assert "refresh_token" not in raw

    def test_hashed_tokens_are_left_alone(self):
        """A failed run is run again, and new workers write hashes before it runs."""
        OAuth2TokenFactory(access="access-token")
        OAuth2TokenFactory(access_token="other-access-token", refresh_token="other-refresh-token")

        migrate()
        migrate()

        for access_token in ("access-token", "other-access-token"):
            response = self.get(
                url_for("api.me"), headers={"Authorization": f"Bearer {access_token}"}
            )
            assert200(response)

    def test_client_secrets_in_clear_are_hashed_and_keep_authenticating(self):
        client = OAuth2ClientFactory(secret=CLIENT_SECRET)
        public_client = OAuth2ClientFactory(secret=None)

        migrate()
        migrate()

        assert public_client.reload().secret is None
        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "client_credentials"},
            headers=basic_header(client),
            json=False,
        )
        assert200(response)

    def test_every_token_is_hashed_across_batches(self):
        """The rewrite is batched: it must not stop at the first batch."""
        for index in range(3):
            OAuth2TokenFactory(access_token=f"access-token-{index}", refresh_token=None)

        # A fresh module per `get()`, so shrinking the batch stays local to this test.
        migration = migrations.get(MIGRATION)
        migration.module.BATCH_SIZE = 2
        migration.migrate(get_db())

        for index in range(3):
            response = self.get(
                url_for("api.me"), headers={"Authorization": f"Bearer access-token-{index}"}
            )
            assert200(response)
