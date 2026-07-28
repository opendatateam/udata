import pytest
from cryptography.fernet import Fernet

TEST_API_BASE = "http://api.example.com"
TEST_DATASTORE_ID = "ds123"
TEST_API_URL = f"{TEST_API_BASE}/datastores/{TEST_DATASTORE_ID}"
TEST_TOKEN = "test-token"
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()

TEST_GEOPF_CONF = pytest.mark.options(
    GEOPF_API_BASE=TEST_API_BASE,
    GEOPF_DATASTORE_ID=TEST_DATASTORE_ID,
    GEOPF_TOKEN_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
)
