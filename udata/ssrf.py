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
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Callable
from urllib.parse import urlsplit

import requests
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import ConnectTimeoutError, NameResolutionError, NewConnectionError
from urllib3.poolmanager import PoolManager
from urllib3.util import Timeout

if TYPE_CHECKING:
    # Private urllib3 aliases, kept out of the runtime imports: a rename in a
    # 2.x release would otherwise turn into an ImportError at startup, since
    # udata.uris imports this module. They are only ever annotations, and
    # ``from __future__ import annotations`` means they are never evaluated.
    from urllib3.util.connection import _TYPE_SOCKET_OPTIONS
    from urllib3.util.timeout import _TYPE_TIMEOUT

__all__ = [
    "SSRFPolicy",
    "BlockedAddressError",
    "BlockedCategory",
    "blocked_reason",
    "SSRFProtectedSession",
]


class BlockedCategory(StrEnum):
    """
    Why an address is refused.

    Callers that phrase their own message (udata's URL validation does) branch on
    the member; the value doubles as a default human-readable reason.
    """

    MULTICAST = "multicast address"
    UNSPECIFIED = "unspecified address"
    LOOPBACK = "loopback address"
    LINK_LOCAL = "link-local address"
    PRIVATE = "private address"
    RESERVED = "reserved address"


class BlockedAddressError(Exception):
    """
    Raised when a request targets an address forbidden by the policy.

    It deliberately does **not** subclass ``OSError``/``requests`` exceptions:
    urllib3's connection retry logic catches ``OSError`` and would otherwise
    swallow the block or retry it. Being a plain ``Exception`` lets it propagate
    straight out of ``session.request()``.
    """


_IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

# RFC 6052 well-known prefix: a DNS64 resolver answers every IPv4-only name with
# ``64:ff9b::<the IPv4>``, and the NAT64 gateway routes it to that IPv4. The
# stdlib has no accessor for it (only the RFC 8215 local-use ``64:ff9b:1::/48``
# is listed as private), so the prefix is spelled out here.
_NAT64_WELL_KNOWN_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


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


def _unwrap_embedded_ipv4(ip: _IPAddress) -> _IPAddress:
    """
    Return the embedded IPv4 address for IPv6 forms that route to one.

    ``::ffff:7f00:1``, ``2002:7f00:1::`` and ``64:ff9b::7f00:1`` all reach
    ``127.0.0.1`` but their IPv6 object reports ``is_loopback == False``. We
    classify the embedded IPv4 so those forms cannot be used to smuggle a
    loopback/private target past the per-category checks — and, symmetrically,
    so a NAT64 address standing for a public IPv4 stays reachable.
    """
    if ip.version == 6:
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return mapped
        sixtofour = ip.sixtofour
        if sixtofour is not None:
            return sixtofour
        if ip in _NAT64_WELL_KNOWN_PREFIX:
            return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip


def blocked_reason(address: str, policy: SSRFPolicy) -> BlockedCategory | None:
    """
    Classify a raw IP string against ``policy``.

    :return: the category that forbids the address, ``None`` when it is allowed.
    """
    ip = _unwrap_embedded_ipv4(ipaddress.ip_address(address))

    # These are never legitimate targets, regardless of policy.
    if ip.is_multicast:
        return BlockedCategory.MULTICAST
    if ip.is_unspecified:
        return BlockedCategory.UNSPECIFIED

    # Specific categories are checked before the broad ``is_private`` because a
    # loopback/link-local address also reports ``is_private == True``; checking
    # the narrow category first lets each be allowed independently.
    if ip.is_loopback:
        return None if policy.allow_loopback else BlockedCategory.LOOPBACK
    if ip.is_link_local:
        return None if policy.allow_link_local else BlockedCategory.LINK_LOCAL
    # Reserved belongs to the narrow group too: the stdlib lists IPv4's
    # 240.0.0.0/4 as private *and* reserved, so testing it after the private
    # branch would make ``allow_reserved`` a no-op for every IPv4 address.
    if ip.is_reserved:
        return None if policy.allow_reserved else BlockedCategory.RESERVED
    # ``is_private`` alone would let CGNAT (100.64.0.0/10) through: the stdlib
    # reports it False there while ``is_global`` is False too. For IPv4 that
    # makes ``not is_global`` a catch-all for whatever IANA reserves next. It
    # buys nothing for IPv6, where the stdlib derives ``is_global`` from
    # ``is_private`` — so site-local (fec0::/10, deprecated by RFC 3879 but
    # still routed here and there, and in none of the stdlib's blocks) has to
    # be named explicitly.
    if ip.is_private or not ip.is_global or (ip.version == 6 and ip.is_site_local):
        return None if policy.allow_private else BlockedCategory.PRIVATE

    return None


def _guarded_create_connection(
    address: tuple[str, int],
    validate: Callable[[str], None],
    timeout: _TYPE_TIMEOUT,
    source_address: tuple[str, int] | None,
    socket_options: _TYPE_SOCKET_OPTIONS | None,
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
            # ``Timeout.DEFAULT_TIMEOUT`` means "leave the socket's default";
            # None means blocking mode — both mirror urllib3's create_connection.
            if timeout is not Timeout.DEFAULT_TIMEOUT:
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

    def __init__(self, *args, policy: SSRFPolicy, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.policy = policy

    def _validate_ip(self, ip: str) -> None:
        reason = blocked_reason(ip, self.policy)
        if reason is not None:
            raise BlockedAddressError(f"{self.host} resolves to a blocked {reason.value} ({ip})")

    def _new_conn(self) -> socket.socket:
        # Same exception mapping as urllib3's own ``_new_conn``: requests relies
        # on it to tell a connect timeout from a refused connection.
        try:
            return _guarded_create_connection(
                (self._dns_host, self.port),
                self._validate_ip,
                self.timeout,
                self.source_address,
                self.socket_options,
            )
        except socket.gaierror as e:
            raise NameResolutionError(self.host, self, e) from e
        except socket.timeout as e:
            raise ConnectTimeoutError(
                self,
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})",
            ) from e
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
    """A ``PoolManager`` whose pools hand out policy-bound guarded connections."""

    def __init__(self, policy: SSRFPolicy, **kwargs):
        super().__init__(**kwargs)
        self.policy = policy

    def _new_pool(
        self,
        scheme: str,
        host: str,
        port: int,
        request_context: dict | None = None,
    ) -> HTTPConnectionPool:
        pool = super()._new_pool(scheme, host, port, request_context)
        connection_cls = GuardedHTTPSConnection if scheme == "https" else GuardedHTTPConnection
        # urllib3 threads connection kwargs through its pool-key namedtuple,
        # which rejects unknown fields — hence binding the policy here rather
        # than passing it as a connection kwarg.
        pool.ConnectionCls = partial(connection_cls, policy=self.policy)
        return pool


class GuardedHTTPAdapter(requests.adapters.HTTPAdapter):
    """A ``requests`` adapter whose connections validate their target IP."""

    def __init__(self, policy: SSRFPolicy, **kwargs):
        self.policy = policy
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = GuardedPoolManager(
            self.policy,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        # requests serves proxied requests from a plain urllib3 ProxyManager,
        # which knows nothing about the guarded pools: going through a proxy
        # would silently disable every check in this module. Fail closed — a
        # proxy able to reach internal hosts is exactly the SSRF target.
        raise BlockedAddressError(
            f"refusing to reach {proxy}: the SSRF guard does not cover proxied connections"
        )


class SSRFProtectedSession(requests.Session):
    """
    A ``requests.Session`` that only reaches destinations allowed by ``policy``.

    Redirects are safe to follow: each hop opens a new guarded connection, so
    an internal redirect target is blocked at connect time like any other.
    """

    def __init__(self, policy: SSRFPolicy | None = None):
        super().__init__()
        self.policy = policy or SSRFPolicy()
        adapter = GuardedHTTPAdapter(policy=self.policy)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def send(self, request, **kwargs):
        scheme = urlsplit(request.url).scheme
        if scheme not in self.policy.allowed_schemes:
            raise BlockedAddressError(f"scheme {scheme!r} is not allowed")
        return super().send(request, **kwargs)
