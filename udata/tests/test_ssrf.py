from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from udata.ssrf import (
    BlockedAddressError,
    SSRFPolicy,
    SSRFProtectedSession,
    blocked_reason,
)

# (address, reason substring or None if allowed under the DEFAULT policy)
DEFAULT_CASES = [
    # Loopback, in every representation that routes to 127.0.0.1 / ::1
    ("127.0.0.1", "loopback"),
    ("127.0.1.1", "loopback"),
    ("::1", "loopback"),
    ("::ffff:7f00:1", "loopback"),  # IPv4-mapped 127.0.0.1
    ("::ffff:127.0.0.1", "loopback"),
    ("2002:7f00:1::", "loopback"),  # 6to4-encoded 127.0.0.1
    # Link-local, incl. the cloud metadata endpoint
    ("169.254.169.254", "link-local"),
    ("::ffff:a9fe:a9fe", "link-local"),  # mapped 169.254.169.254
    ("2002:a9fe:a9fe::", "link-local"),  # 6to4-encoded 169.254.169.254
    ("fe80::1", "link-local"),
    # Private (RFC1918 / ULA)
    ("10.0.0.1", "private"),
    ("192.168.1.1", "private"),
    ("172.16.0.1", "private"),
    ("::ffff:0a00:0001", "private"),  # mapped 10.0.0.1
    ("fc00::1", "private"),
    # CGNAT (RFC 6598): ``ipaddress`` reports it neither private nor reserved,
    # only not globally routable.
    ("100.64.0.1", "private"),
    ("100.127.255.254", "private"),
    ("::ffff:6440:1", "private"),  # mapped 100.64.0.1
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
def test_blocked_reason_default_policy(address, reason):
    result = blocked_reason(address, SSRFPolicy())
    if reason is None:
        assert result is None, f"{address} should be allowed, got {result!r}"
    else:
        assert result is not None and reason in result, (
            f"{address} should be blocked as {reason}, got {result!r}"
        )


def test_allow_loopback_permits_loopback_only():
    policy = SSRFPolicy(allow_loopback=True)
    assert blocked_reason("127.0.0.1", policy) is None
    assert blocked_reason("::ffff:7f00:1", policy) is None  # mapped form too
    assert blocked_reason("2002:7f00:1::", policy) is None  # 6to4 form too
    # But a private (non-loopback) address is still blocked.
    assert blocked_reason("10.0.0.1", policy) is not None


def test_allow_private_does_not_permit_loopback():
    policy = SSRFPolicy(allow_private=True)
    assert blocked_reason("10.0.0.1", policy) is None
    assert blocked_reason("100.64.0.1", policy) is None  # CGNAT counts as private
    assert blocked_reason("169.254.169.254", policy) is not None  # link-local stays blocked
    assert blocked_reason("127.0.0.1", policy) is not None  # loopback stays blocked
    assert blocked_reason("::7f00:1", policy) is not None  # reserved stays blocked


def test_allow_reserved_permits_reserved_only():
    policy = SSRFPolicy(allow_reserved=True)
    # IPv4-compatible IPv6 is deprecated and no longer routed to the embedded
    # IPv4 address, so it is classified reserved rather than loopback: opening
    # up reserved does not open up 127.0.0.1.
    assert blocked_reason("::7f00:1", policy) is None
    assert blocked_reason("::127.0.0.1", policy) is None
    assert blocked_reason("127.0.0.1", policy) is not None
    assert blocked_reason("10.0.0.1", policy) is not None


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


def test_session_ignores_environment_proxy(monkeypatch):
    # requests serves proxied requests from a plain urllib3 ProxyManager, which
    # knows nothing about the guarded pools. An ambient proxy variable must not
    # be able to turn the guard off.
    monkeypatch.setenv("HTTP_PROXY", "http://198.51.100.1:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://198.51.100.1:3128")
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://127.0.0.1:9/", timeout=2)


def test_session_refuses_explicit_proxy():
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="proxied"):
        session.get("http://142.42.1.1/", timeout=2, proxies={"http": "http://198.51.100.1:3128"})


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
