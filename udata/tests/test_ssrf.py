from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from udata.ssrf import (
    BlockedAddressError,
    SSRFPolicy,
    SSRFProtectedSession,
    is_ip_blocked,
)

# (address, reason substring or None if allowed under the DEFAULT policy)
DEFAULT_CASES = [
    # Loopback, in every representation that routes to 127.0.0.1 / ::1
    ("127.0.0.1", "loopback"),
    ("127.0.1.1", "loopback"),
    ("::1", "loopback"),
    ("::ffff:7f00:1", "loopback"),  # IPv4-mapped 127.0.0.1 — the reported bypass
    ("::ffff:127.0.0.1", "loopback"),
    # Link-local, incl. the cloud metadata endpoint
    ("169.254.169.254", "link-local"),
    ("::ffff:a9fe:a9fe", "link-local"),  # mapped 169.254.169.254
    ("fe80::1", "link-local"),
    # Private (RFC1918 / ULA)
    ("10.0.0.1", "private"),
    ("192.168.1.1", "private"),
    ("172.16.0.1", "private"),
    ("::ffff:0a00:0001", "private"),  # mapped 10.0.0.1
    ("fc00::1", "private"),
    # Reserved / IPv4-compatible IPv6
    ("::7f00:1", "reserved"),
    ("::127.0.0.1", "reserved"),
    # Multicast / unspecified are always blocked
    ("224.0.0.1", "multicast"),
    ("ff00::1", "multicast"),
    ("0.0.0.0", "unspecified"),
    ("::", "unspecified"),
    # Public addresses are allowed
    ("142.42.1.1", None),
    ("8.8.8.8", None),
    ("2a00:1450:4007:80e::2004", None),
]


@pytest.mark.parametrize("address,reason", DEFAULT_CASES)
def test_is_ip_blocked_default_policy(address, reason):
    result = is_ip_blocked(address, SSRFPolicy())
    if reason is None:
        assert result is None, f"{address} should be allowed, got {result!r}"
    else:
        assert result is not None and reason in result, (
            f"{address} should be blocked as {reason}, got {result!r}"
        )


def test_allow_loopback_permits_loopback_only():
    policy = SSRFPolicy(allow_loopback=True)
    assert is_ip_blocked("127.0.0.1", policy) is None
    assert is_ip_blocked("::ffff:7f00:1", policy) is None  # mapped form too
    # But a private (non-loopback) address is still blocked.
    assert is_ip_blocked("10.0.0.1", policy) is not None


def test_allow_private_does_not_permit_loopback():
    policy = SSRFPolicy(allow_private=True)
    assert is_ip_blocked("10.0.0.1", policy) is None
    assert is_ip_blocked("169.254.169.254", policy) is not None  # link-local stays blocked
    assert is_ip_blocked("127.0.0.1", policy) is not None  # loopback stays blocked


def test_session_blocks_loopback_before_connecting():
    session = SSRFProtectedSession()
    # Nothing needs to listen on this port: the block happens before connect().
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://127.0.0.1:9/", timeout=2)


def test_session_blocks_ipv4_mapped_loopback():
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://[::ffff:7f00:1]:9/", timeout=2)


def test_session_blocks_hostname_resolving_to_loopback():
    # The anti-rebinding property: the block is decided on the address the socket
    # actually resolves to at connect time, not on the URL string. ``localhost``
    # resolves to a loopback address.
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://localhost:9/", timeout=2)


def test_session_rejects_disallowed_scheme():
    session = SSRFProtectedSession(SSRFPolicy(allowed_schemes=frozenset({"https"})))
    with pytest.raises(BlockedAddressError, match="scheme"):
        session.get("http://142.42.1.1/", timeout=2)


def test_session_enforces_allowed_ports():
    session = SSRFProtectedSession(SSRFPolicy(allow_loopback=True, allowed_ports=frozenset({443})))
    with pytest.raises(BlockedAddressError, match="port"):
        session.get("http://127.0.0.1:9/", timeout=2)


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


def test_session_allows_permitted_target_end_to_end(local_server):
    # The whole guarded chain (adapter → pool → connection → validated connect)
    # must let an allowed address through, not only block forbidden ones.
    host, port = local_server
    session = SSRFProtectedSession(SSRFPolicy(allow_loopback=True))
    response = session.get(f"http://{host}:{port}/", timeout=5)
    assert response.status_code == 200
    assert response.text == "hello from allowed host"
