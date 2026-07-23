import pytest

from udata.http import ssrf_policy, ssrf_session
from udata.ssrf import BlockedAddressError
from udata.tests import PytestOnlyTestCase


class SSRFSessionFactoryTest(PytestOnlyTestCase):
    @pytest.mark.options(URLS_ALLOW_LOCAL=False, URLS_ALLOW_PRIVATE=False)
    def test_policy_is_strict_by_default(self):
        policy = ssrf_policy()
        assert policy.allow_loopback is False
        assert policy.allow_private is False
        assert policy.allow_link_local is False
        assert policy.allow_reserved is False

    @pytest.mark.options(URLS_ALLOW_LOCAL=True, URLS_ALLOW_PRIVATE=True)
    def test_policy_follows_url_settings(self):
        policy = ssrf_policy()
        assert policy.allow_loopback is True
        # udata groups link-local and reserved under URLS_ALLOW_PRIVATE.
        assert policy.allow_private is True
        assert policy.allow_link_local is True
        assert policy.allow_reserved is True

    @pytest.mark.options(URLS_ALLOW_LOCAL=False, URLS_ALLOW_PRIVATE=False)
    def test_session_blocks_loopback_when_settings_are_strict(self):
        with pytest.raises(BlockedAddressError, match="loopback"):
            ssrf_session().get("http://127.0.0.1:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOW_LOCAL=False, URLS_ALLOW_PRIVATE=False)
    def test_session_blocks_ipv4_mapped_loopback(self):
        with pytest.raises(BlockedAddressError, match="loopback"):
            ssrf_session().get("http://[::ffff:7f00:1]:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOW_LOCAL=True)
    def test_session_allows_loopback_when_settings_permit(self):
        # With URLS_ALLOW_LOCAL, loopback is no longer blocked: the connection is
        # attempted and fails on the closed port instead of BlockedAddressError.
        with pytest.raises(Exception) as excinfo:
            ssrf_session().get("http://127.0.0.1:9/", timeout=2)
        assert not isinstance(excinfo.value, BlockedAddressError)
