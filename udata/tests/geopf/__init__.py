from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet

from udata.geopf.models import GeopfToken

TEST_API_BASE = "http://api.example.com"
TEST_DATASTORE_ID = "ds123"
TEST_API_URL = f"{TEST_API_BASE}/datastores/{TEST_DATASTORE_ID}"
TEST_TOKEN = "test-token"
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()

TEST_GEOPF_CONF = pytest.mark.options(
    GEOPF_API_BASE=TEST_API_BASE,
    GEOPF_TOKEN_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
)


def create_geopf_token(user, access_token="a", refresh_token="r", expires_at=None, save=True):
    token = GeopfToken(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at or datetime.now(UTC) + timedelta(hours=1),
    )
    if save:
        token.save()
    return token
