import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from udata.ssrf import (
    BlockedAddressError,
    BlockedCategory,
    SSRFPolicy,
    SSRFProtectedSession,
    blocked_reason,
)

# Every request here crosses requests' proxy resolution, and a proxied request
# never reaches the guard: neutralise the environment so these tests assert the
# code's behaviour rather than the machine's proxy settings.
pytestmark = pytest.mark.usefixtures("no_ambient_proxy")

# (address, category that forbids it, or None if allowed under the DEFAULT policy)
DEFAULT_CASES = [
    # Loopback, in every representation that routes to 127.0.0.1 / ::1
    ("127.0.0.1", BlockedCategory.LOOPBACK),
    ("127.0.1.1", BlockedCategory.LOOPBACK),
    ("::1", BlockedCategory.LOOPBACK),
    ("::ffff:7f00:1", BlockedCategory.LOOPBACK),  # IPv4-mapped 127.0.0.1
    ("::ffff:127.0.0.1", BlockedCategory.LOOPBACK),
    ("2002:7f00:1::", BlockedCategory.LOOPBACK),  # 6to4-encoded 127.0.0.1
    ("64:ff9b::7f00:1", BlockedCategory.LOOPBACK),  # NAT64 well-known prefix, 127.0.0.1
    ("64:ff9b::127.0.0.1", BlockedCategory.LOOPBACK),
    # Link-local, incl. the cloud metadata endpoint
    ("169.254.169.254", BlockedCategory.LINK_LOCAL),
    ("::ffff:a9fe:a9fe", BlockedCategory.LINK_LOCAL),  # mapped 169.254.169.254
    ("2002:a9fe:a9fe::", BlockedCategory.LINK_LOCAL),  # 6to4-encoded 169.254.169.254
    ("64:ff9b::a9fe:a9fe", BlockedCategory.LINK_LOCAL),  # NAT64-encoded 169.254.169.254
    ("fe80::1", BlockedCategory.LINK_LOCAL),
    # Private (RFC1918 / ULA)
    ("10.0.0.1", BlockedCategory.PRIVATE),
    ("192.168.1.1", BlockedCategory.PRIVATE),
    ("172.16.0.1", BlockedCategory.PRIVATE),
    ("::ffff:0a00:0001", BlockedCategory.PRIVATE),  # mapped 10.0.0.1
    ("64:ff9b::a00:1", BlockedCategory.PRIVATE),  # NAT64-encoded 10.0.0.1
    ("fc00::1", BlockedCategory.PRIVATE),
    # Site-local (RFC 3879): deprecated but still routed on some networks, and
    # the stdlib reports it neither private nor reserved.
    ("fec0::1", BlockedCategory.PRIVATE),
    ("feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", BlockedCategory.PRIVATE),
    # CGNAT (RFC 6598): ``ipaddress`` reports it neither private nor reserved,
    # only not globally routable.
    ("100.64.0.1", BlockedCategory.PRIVATE),
    ("100.127.255.254", BlockedCategory.PRIVATE),
    ("::ffff:6440:1", BlockedCategory.PRIVATE),  # mapped 100.64.0.1
    # Reserved: IETF future use (240.0.0.0/4) and IPv4-compatible IPv6
    ("240.0.0.1", BlockedCategory.RESERVED),
    ("255.255.255.255", BlockedCategory.RESERVED),
    ("::7f00:1", BlockedCategory.RESERVED),
    ("::127.0.0.1", BlockedCategory.RESERVED),
    # Multicast / unspecified are always blocked
    ("224.0.0.1", BlockedCategory.MULTICAST),
    ("ff00::1", BlockedCategory.MULTICAST),
    ("0.0.0.0", BlockedCategory.UNSPECIFIED),
    ("::", BlockedCategory.UNSPECIFIED),
    # Public addresses are allowed
    ("142.42.1.1", None),
    ("8.8.8.8", None),
    ("2a00:1450:4007:80e::2004", None),
    # A DNS64 resolver hands out the NAT64 form of every IPv4-only host: the
    # public ones must stay reachable, or nothing resolves on such a network.
    ("64:ff9b::8.8.8.8", None),
    ("64:ff9b::808:808", None),
]


@pytest.mark.parametrize("address,expected", DEFAULT_CASES)
def test_blocked_reason_default_policy(address, expected):
    assert blocked_reason(address, SSRFPolicy()) is expected


def test_allow_loopback_permits_loopback_only():
    policy = SSRFPolicy(allow_loopback=True)
    assert blocked_reason("127.0.0.1", policy) is None
    assert blocked_reason("::ffff:7f00:1", policy) is None  # mapped form too
    assert blocked_reason("2002:7f00:1::", policy) is None  # 6to4 form too
    assert blocked_reason("64:ff9b::7f00:1", policy) is None  # NAT64 form too
    # But a private (non-loopback) address is still blocked.
    assert blocked_reason("10.0.0.1", policy) is not None


def test_allow_private_does_not_permit_loopback():
    policy = SSRFPolicy(allow_private=True)
    assert blocked_reason("10.0.0.1", policy) is None
    assert blocked_reason("100.64.0.1", policy) is None  # CGNAT counts as private
    assert blocked_reason("fec0::1", policy) is None  # site-local counts as private
    assert blocked_reason("169.254.169.254", policy) is not None  # link-local stays blocked
    assert blocked_reason("127.0.0.1", policy) is not None  # loopback stays blocked
    assert blocked_reason("64:ff9b::7f00:1", policy) is not None  # NAT64 loopback stays blocked
    assert blocked_reason("::7f00:1", policy) is not None  # reserved stays blocked


def test_allow_reserved_permits_reserved_only():
    policy = SSRFPolicy(allow_reserved=True)
    assert blocked_reason("240.0.0.1", policy) is None  # IETF future use
    # IPv4-compatible IPv6 is deprecated and no longer routed to the embedded
    # IPv4 address, so it is classified reserved rather than loopback: opening
    # up reserved does not open up 127.0.0.1.
    assert blocked_reason("::7f00:1", policy) is None
    assert blocked_reason("::127.0.0.1", policy) is None
    assert blocked_reason("127.0.0.1", policy) is not None
    assert blocked_reason("10.0.0.1", policy) is not None


def test_allow_private_does_not_permit_reserved():
    # 240.0.0.0/4 reports both ``is_private`` and ``is_reserved``: the two flags
    # must stay independently controllable despite the overlap.
    policy = SSRFPolicy(allow_private=True)
    assert blocked_reason("10.0.0.1", policy) is None
    assert blocked_reason("240.0.0.1", policy) is BlockedCategory.RESERVED


def test_session_blocks_loopback_before_connecting():
    session = SSRFProtectedSession()
    # Nothing needs to listen on this port: the block happens before connect().
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://127.0.0.1:9/", timeout=2)


def test_session_blocks_ipv4_mapped_loopback():
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("http://[::ffff:7f00:1]:9/", timeout=2)


def test_session_blocks_an_https_target():
    # The https pool hands out a different connection class than the http one
    # (GuardedHTTPSConnection): without this, only the plain-HTTP wiring is ever
    # built, while every real harvest source is https.
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="loopback"):
        session.get("https://127.0.0.1:9/", timeout=2)


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


def test_session_refuses_an_environment_proxy(monkeypatch):
    # requests serves proxied requests from a plain urllib3 ProxyManager, which
    # knows nothing about the guarded pools. A proxy picked up from the
    # environment must fail like an explicit one, not silently turn the guard off.
    monkeypatch.setenv("HTTP_PROXY", "http://198.51.100.1:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://198.51.100.1:3128")
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="proxied"):
        session.get("http://127.0.0.1:9/", timeout=2)


def test_session_refuses_explicit_proxy():
    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="proxied"):
        session.get("http://142.42.1.1/", timeout=2, proxies={"http": "http://198.51.100.1:3128"})


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect-to-metadata":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
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


def resolving_to(addresses):
    """A ``socket.getaddrinfo`` stub answering with the given IPs, in order."""

    def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))
            for ip in addresses
        ]

    return getaddrinfo


@pytest.mark.parametrize("blocked_first", [True, False])
def test_session_connects_to_the_allowed_address_of_a_multi_homed_host(
    local_server, monkeypatch, blocked_first
):
    # A hostname resolving to both an internal and an allowed address must stay
    # reachable through the allowed one — a blocked candidate rules out itself,
    # not the whole host — whatever order the resolver hands them out in.
    host, port = local_server
    addresses = ["10.0.0.1", host] if blocked_first else [host, "10.0.0.1"]
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to(addresses))

    session = SSRFProtectedSession(SSRFPolicy(allow_loopback=True))
    response = session.get(f"http://multi-homed.test:{port}/", timeout=5)

    assert response.status_code == 200
    assert response.text == "hello from allowed host"


def test_session_blocks_a_host_whose_addresses_are_all_forbidden(monkeypatch):
    # The counterpart: skipping blocked candidates must not end up letting a
    # fully internal host through silently.
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to(["10.0.0.1", "192.168.1.1"]))

    session = SSRFProtectedSession()
    with pytest.raises(BlockedAddressError, match="private"):
        session.get("http://internal-only.test:9/", timeout=2)


def test_session_blocks_a_redirect_to_a_forbidden_target(local_server):
    # A validated URL can 302 to an internal target. Every hop opens a new
    # guarded connection, so the block lands on the redirect target — here the
    # cloud metadata endpoint — rather than on the allowed first hop.
    host, port = local_server
    session = SSRFProtectedSession(SSRFPolicy(allow_loopback=True))
    with pytest.raises(BlockedAddressError, match="link-local"):
        session.get(f"http://{host}:{port}/redirect-to-metadata", timeout=5)
