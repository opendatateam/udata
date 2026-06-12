import pytest

TEST_API_BASE = "http://api.example.com"
TEST_DATASTORE_ID = "ds123"
TEST_API_URL = f"{TEST_API_BASE}/datastores/{TEST_DATASTORE_ID}"

TEST_GEOPF_CONF = pytest.mark.options(
    GEOPF_API_BASE=TEST_API_BASE,
    GEOPF_TOKEN="test-token",
    GEOPF_DATASTORE_ID=TEST_DATASTORE_ID,
)
