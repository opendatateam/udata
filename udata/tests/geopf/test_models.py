from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from flask import current_app

from udata.core.user.factories import UserFactory
from udata.geopf.models import GeopfToken
from udata.mongo.encrypted_field import CIPHERTEXT_PREFIX
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_GEOPF_CONF


@TEST_GEOPF_CONF
class GeopfTokenTest(PytestOnlyDBTestCase):
    def test_round_trips_encrypted_fields(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="plain-access",
            refresh_token="plain-refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        token.save()

        raw = GeopfToken._get_collection().find_one({"_id": token.id})
        assert raw["access_token"].startswith(CIPHERTEXT_PREFIX)
        assert raw["refresh_token"].startswith(CIPHERTEXT_PREFIX)
        assert "plain-access" not in raw["access_token"]
        assert "plain-refresh" not in raw["refresh_token"]

        reloaded = GeopfToken.objects.get(id=token.id)
        assert reloaded.access_token == "plain-access"
        assert reloaded.refresh_token == "plain-refresh"

    def test_wrong_key_raises_instead_of_returning_ciphertext(self):
        user = UserFactory()
        GeopfToken(
            user=user,
            access_token="plain-access",
            refresh_token="plain-refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ).save()

        other_key = Fernet.generate_key().decode()
        with pytest.raises(RuntimeError, match="GEOPF_TOKEN_ENCRYPTION_KEY"):
            with patch.dict(current_app.config, GEOPF_TOKEN_ENCRYPTION_KEY=other_key):
                GeopfToken.objects(user=user).first()

    def test_is_expired_true_in_the_past(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        assert token.is_expired()

    def test_is_expired_false_in_the_future(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert not token.is_expired()
