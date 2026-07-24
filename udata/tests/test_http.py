from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from udata import http, uris
from udata.tests import PytestOnlyTestCase
from udata.uris import ValidationError

# (address, reason substring or None if allowed under the default policy)
DEFAULT_CASES = [
    # Loopback, in every representation that routes to 127.0.0.1 / ::1
    ("https://127.0.0.1", "loopback"),
    ("https://127.0.1.1", "loopback"),
    ("https://[::1]", "loopback"),
    ("https://[::ffff:7f00:1]", "loopback"),  # IPv4-mapped 127.0.0.1 — the reported bypass
    ("https://[::ffff:127.0.0.1]", "loopback"),
    # Link-local, incl. the cloud metadata endpoint
    ("https://169.254.169.254", "link-local"),
    ("https://[::ffff:a9fe:a9fe]", "link-local"),  # mapped 169.254.169.254
    ("https://[fe80::1]", "link-local"),
    # Private (RFC1918 / ULA)
    ("https://10.0.0.1", "private"),
    ("https://192.168.1.1", "private"),
    ("https://172.16.0.1", "private"),
    ("https://[::ffff:0a00:0001]", "private"),  # mapped 10.0.0.1
    ("https://fc00::1", "private"),
    # Reserved / IPv4-compatible IPv6
    ("https://[::7f00:1]", "reserved"),
    ("https://[::127.0.0.1]", "reserved"),
    # Multicast / unspecified are always blocked
    ("https://224.0.0.1", "multicast"),
    ("https://[ff00::1]", "multicast"),
    ("https://0.0.0.0", "unspecified"),
    ("https://[::]", "unspecified"),
    # Public addresses are allowed
    ("https://142.42.1.1", None),
    ("https://8.8.8.8", None),
    ("https://[2a00:1450:4007:80e::2004]", None),
]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello from allowed host"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address
    server.shutdown()


class SSRFSessionFactoryTest(PytestOnlyTestCase):
    @pytest.mark.options(URLS_ALLOW_LOCAL=False, URLS_ALLOW_PRIVATE=False)
    def test_session_blocks_loopback_when_settings_are_strict(self):
        with pytest.raises(ValidationError, match="invalide"):
            http.get(url="http://127.0.0.1:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOW_LOCAL=False, URLS_ALLOW_PRIVATE=False)
    def test_session_blocks_ipv4_mapped_loopback(self):
        with pytest.raises(ValidationError, match="invalide"):
            http.get("http://[::ffff:7f00:1]:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOW_LOCAL=True)
    def test_session_allows_loopback_when_settings_permit(self):
        # With URLS_ALLOW_LOCAL, loopback is no longer blocked: the connection is
        # attempted and fails on the closed port instead of ValidationError.
        with pytest.raises(Exception) as excinfo:
            http.get("http://127.0.0.1:90/", timeout=2)
        assert not isinstance(excinfo.value, ValidationError)

    @pytest.mark.options(URLS_ALLOW_LOCAL=False)
    @pytest.mark.parametrize("address,reason", DEFAULT_CASES)
    def test_is_ip_blocked_default_policy(self, address, reason):
        if reason:
            with pytest.raises(ValidationError, match="invalide"):
                uris.validate(address)
        else:
            uris.validate(address)

    @pytest.mark.options(URLS_ALLOW_LOCAL=True)
    def test_allow_loopback_permits_loopback_only(
        self,
    ):
        assert uris.validate("http://127.0.0.1") is not None
        assert uris.validate("http://[::ffff:7f00:1]") is not None
        # But a private (non-loopback) address is still blocked.
        with pytest.raises(ValidationError, match="invalide"):
            uris.validate("http://10.0.0.1")

    @pytest.mark.options(URLS_ALLOW_LOCAL=False)
    @pytest.mark.options(URLS_ALLOW_PRIVATE=True)
    def test_allow_private_does_not_permit_loopback(
        self,
    ):
        assert uris.validate("http://10.0.0.1") is not None
        with pytest.raises(ValidationError, match="invalide"):
            uris.validate("http://169.254.169.254")  # link-local stays blocked
        with pytest.raises(ValidationError, match="invalide"):
            uris.validate("http://127.0.0.1")  # loopback stays blocked

    def test_session_blocks_loopback_before_connecting(
        self,
    ):
        # Nothing needs to listen on this port: the block happens before connect().
        with pytest.raises(ValidationError, match="invalide"):
            http.get("http://127.0.0.1:9/", timeout=2)

    def test_session_blocks_hostname_resolving_to_loopback(
        self,
    ):
        # The anti-rebinding property: the block is decided on the address the socket
        # actually resolves to at connect time, not on the URL string. ``localhost``
        # resolves to a loopback address.
        with pytest.raises(ValidationError, match="invalide"):
            http.get("http://localhost:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOWED_SCHEMES=frozenset({"https"}))
    def test_session_rejects_disallowed_scheme(
        self,
    ):
        with pytest.raises(ValidationError, match="Schéma"):
            http.get("http://142.42.1.1/", timeout=2)

    def test_session_enforces_valid_ports(
        self,
    ):
        with pytest.raises(ValidationError, match="invalide"):
            http.get("http://127.0.0.1:9/", timeout=2)

    @pytest.mark.options(URLS_ALLOW_LOCAL=True)
    def test_session_allows_permitted_target_end_to_end(self, local_server):
        # The whole guarded chain (adapter → pool → connection → validated connect)
        # must let an allowed address through, not only block forbidden ones.
        host, port = local_server
        response = http.get(f"http://{host}:{port}/", timeout=5)
        assert response.status_code == 200
        assert response.text == "hello from allowed host"
