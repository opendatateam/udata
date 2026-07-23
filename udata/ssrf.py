"""
SSRF-hardened HTTP client for the ``requests`` library.

This module is intentionally self-contained: it has **no dependency on udata**
(no config, no i18n, no Flask). It only depends on the standard library,
``requests`` and ``urllib3``. It can be lifted out of this repository and
published as a standalone package by copying this single file — do not import
anything from ``udata`` here.

Why this exists
---------------
The naive way to prevent Server-Side Request Forgery is to validate the URL
string (or resolve its hostname) *before* handing it to ``requests``. That
approach is structurally broken:

* **DNS rebinding (TOCTOU)** — the hostname resolved at validation time is not
  the address the socket connects to later. An attacker returns a public IP for
  the check and a private one for the real request.
* **Address representation gaps** — IPv4-mapped IPv6 (``::ffff:7f00:1``),
  IPv4-compatible (``::7f00:1``), octal/integer forms… a string filter keeps
  missing new encodings.
* **Redirects** — a validated URL can ``302`` to an internal target.

The only robust fix is to validate the IP **at the moment the socket connects**,
using the very address the socket will use. That is what this module does: a
custom ``urllib3`` connection validates each candidate IP right before
``connect()``. Because validation and connection share the same resolution,
there is no rebinding window; because every redirect hop opens a new guarded
connection, redirects are validated too.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Callable

import requests
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.poolmanager import PoolManager
from urllib3.util.retry import Retry
from urllib3.util.timeout import _DEFAULT_TIMEOUT

__all__ = [
    "SSRFPolicy",
    "BlockedAddressError",
    "is_ip_blocked",
    "GuardedHTTPAdapter",
    "SSRFProtectedSession",
]


class BlockedAddressError(Exception):
    """
    Raised when a request targets an address forbidden by the policy.

    It deliberately does **not** subclass ``OSError``/``requests`` exceptions:
    urllib3's connection retry logic catches ``OSError`` and would otherwise
    swallow the block or retry it. Being a plain ``Exception`` lets it propagate
    straight out of ``session.request()``.
    """


_IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


@dataclass(frozen=True)
class SSRFPolicy:
    """
    Which destinations an :class:`SSRFProtectedSession` is allowed to reach.

    Everything that is not a globally routable (public) address is blocked by
    default. Individual categories can be re-enabled — typically only in tests
    or trusted internal tooling.
    """

    allow_loopback: bool = False  # 127.0.0.0/8, ::1
    allow_private: bool = False  # RFC1918, ULA (fc00::/7), CGNAT…
    allow_link_local: bool = False  # 169.254.0.0/16, fe80::/10 (cloud metadata!)
    allow_reserved: bool = False  # IETF-reserved / IPv4-compatible IPv6, etc.
    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    # ``None`` means "any port". Otherwise only these ports are reachable.
    allowed_ports: frozenset[int] | None = None
    # Optional escape hatch for deployments doing split-horizon DNS: a hostname
    # for which this returns True bypasses the IP checks entirely. Use sparingly.
    hostname_allowlist: Callable[[str], bool] | None = field(default=None, compare=False)


def _unwrap_embedded_ipv4(ip: _IPAddress) -> _IPAddress:
    """
    Return the embedded IPv4 address for IPv6 forms that route to one.

    ``::ffff:7f00:1`` and ``2002:7f00:1::`` both reach ``127.0.0.1`` but their
    IPv6 object reports ``is_loopback == False``. We classify the embedded IPv4
    so those forms cannot be used to smuggle a loopback/private target past the
    per-category checks.
    """
    if ip.version == 6:
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return mapped
        sixtofour = ip.sixtofour
        if sixtofour is not None:
            return sixtofour
    return ip


def is_ip_blocked(address: str, policy: SSRFPolicy) -> str | None:
    """
    Classify a raw IP string against ``policy``.

    :return: a short reason string when the address is blocked, ``None`` when it
        is allowed.
    """
    ip = _unwrap_embedded_ipv4(ipaddress.ip_address(address))

    # These are never legitimate targets, regardless of policy.
    if ip.is_multicast:
        return "multicast address"
    if ip.is_unspecified:
        return "unspecified address"

    # Specific categories are checked before the broad ``is_private`` because a
    # loopback/link-local address also reports ``is_private == True``; checking
    # the narrow category first lets each be allowed independently.
    if ip.is_loopback:
        return None if policy.allow_loopback else "loopback address"
    if ip.is_link_local:
        return None if policy.allow_link_local else "link-local address"
    if ip.is_private:
        return None if policy.allow_private else "private address"
    if ip.is_reserved:
        return None if policy.allow_reserved else "reserved address"

    return None


def _guarded_create_connection(
    address: tuple[str, int],
    validate: Callable[[str], None],
    timeout,
    source_address,
    socket_options,
) -> socket.socket:
    """
    ``urllib3.util.connection.create_connection`` with an IP check.

    Mirrors urllib3's connector but calls ``validate(ip)`` on each resolved
    candidate right before ``connect()``. Resolution and connection share the
    same ``getaddrinfo`` result, so there is no rebinding window.
    """
    host, port = address
    if host.startswith("["):
        host = host.strip("[]")

    err = None
    for af, socktype, proto, _canonname, sa in socket.getaddrinfo(
        host, port, socket.AF_UNSPEC, socket.SOCK_STREAM
    ):
        # sa[0] is the exact IP the socket would connect to.
        validate(sa[0])
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            for opt in socket_options or ():
                sock.setsockopt(*opt)
            # ``_DEFAULT_TIMEOUT`` means "leave the socket's default"; None means
            # blocking mode — both mirror urllib3's own create_connection.
            if timeout is not _DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock
        except OSError as e:
            err = e
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    raise OSError("getaddrinfo returns an empty list")


class _GuardedConnectionMixin:
    """Shared ``_new_conn`` that validates the resolved IP before connecting."""

    # Bound per-policy by ``GuardedPoolManager`` via a generated subclass. We use
    # a class attribute rather than a constructor kwarg because urllib3 threads
    # connection kwargs through its pool-key namedtuple, which rejects unknown
    # fields.
    policy: SSRFPolicy = SSRFPolicy()

    def _validate_ip(self, ip: str) -> None:
        reason = is_ip_blocked(ip, self.policy)
        if reason is not None:
            raise BlockedAddressError(f"{self.host} resolves to a blocked {reason} ({ip})")
        if self.policy.allowed_ports is not None and self.port not in self.policy.allowed_ports:
            raise BlockedAddressError(f"port {self.port} is not allowed")

    def _new_conn(self) -> socket.socket:
        if self.policy.hostname_allowlist and self.policy.hostname_allowlist(self.host):
            return super()._new_conn()
        try:
            return _guarded_create_connection(
                (self._dns_host, self.port),
                self._validate_ip,
                self.timeout,
                self.source_address,
                self.socket_options,
            )
        except OSError as e:
            raise NewConnectionError(self, f"Failed to establish a new connection: {e}") from e


class GuardedHTTPConnection(_GuardedConnectionMixin, HTTPConnection):
    pass


class GuardedHTTPSConnection(_GuardedConnectionMixin, HTTPSConnection):
    # TLS handshake happens in ``connect()`` after ``_new_conn`` returns the raw
    # socket, still using ``self.host`` for SNI and certificate validation — so
    # connecting to a validated IP keeps hostname verification intact.
    pass


class GuardedPoolManager(PoolManager):
    def __init__(self, policy: SSRFPolicy, **kwargs):
        # Generate per-policy connection subclasses carrying the policy as a
        # class attribute, and pools that use them. This keeps the policy out of
        # urllib3's connection kwargs (see ``_GuardedConnectionMixin.policy``).
        http_conn = type("PolicyHTTPConnection", (GuardedHTTPConnection,), {"policy": policy})
        https_conn = type("PolicyHTTPSConnection", (GuardedHTTPSConnection,), {"policy": policy})
        super().__init__(**kwargs)
        # Must be set after super().__init__, which resets pool_classes_by_scheme
        # to urllib3's module-level default.
        self.pool_classes_by_scheme = {
            "http": type("PolicyHTTPPool", (HTTPConnectionPool,), {"ConnectionCls": http_conn}),
            "https": type("PolicyHTTPSPool", (HTTPSConnectionPool,), {"ConnectionCls": https_conn}),
        }


class GuardedHTTPAdapter(requests.adapters.HTTPAdapter):
    """A ``requests`` adapter whose connections validate their target IP."""

    def __init__(self, policy: SSRFPolicy | None = None, **kwargs):
        self.policy = policy or SSRFPolicy()
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = GuardedPoolManager(
            self.policy,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


class SSRFProtectedSession(requests.Session):
    """
    A ``requests.Session`` that only reaches destinations allowed by ``policy``.

    Redirects are safe to follow: each hop opens a new guarded connection, so
    an internal redirect target is blocked at connect time like any other.
    """

    def __init__(self, policy: SSRFPolicy | None = None, max_retries: int | Retry = 0):
        super().__init__()
        self.policy = policy or SSRFPolicy()
        adapter = GuardedHTTPAdapter(policy=self.policy, max_retries=max_retries)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def send(self, request, **kwargs):
        scheme = request.url.split("://", 1)[0].lower()
        if scheme not in self.policy.allowed_schemes:
            raise BlockedAddressError(f"scheme {scheme!r} is not allowed")
        return super().send(request, **kwargs)
