"""
Central outbound HTTP for udata, hardened against SSRF.

This is the junction between the udata-agnostic :mod:`udata.ssrf` module and
udata's configuration: the SSRF policy is derived from the ``URLS_ALLOW_*``
settings (the same knobs that drive :func:`udata.uris.validate`).

Use :func:`ssrf_session` for **any** fetch of a URL that comes, directly or
indirectly, from user input — harvest sources, dataservice documentation, etc.
Trusted operator-configured integrations (metrics API, webhooks, OAuth
providers…) are not an SSRF vector and may legitimately target internal hosts;
they intentionally do not go through this guard.
"""

from __future__ import annotations

from flask import current_app

from udata.ssrf import SSRFPolicy, SSRFProtectedSession


def ssrf_policy() -> SSRFPolicy:
    """Build an :class:`SSRFPolicy` from the current app's ``URLS_ALLOW_*`` config."""
    config = current_app.config
    # udata groups link-local and IETF-reserved ranges under "private" (see
    # udata.uris.validate), so a single URLS_ALLOW_PRIVATE toggle drives them all.
    allow_private = config["URLS_ALLOW_PRIVATE"]
    return SSRFPolicy(
        allow_loopback=config["URLS_ALLOW_LOCAL"],
        allow_private=allow_private,
        allow_link_local=allow_private,
        allow_reserved=allow_private,
        allowed_schemes=frozenset(config["URLS_ALLOWED_SCHEMES"]),
    )


def ssrf_session(**kwargs) -> SSRFProtectedSession:
    """Return a :class:`SSRFProtectedSession` configured from the app settings."""
    return SSRFProtectedSession(ssrf_policy(), **kwargs)
