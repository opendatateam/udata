"""
Central outbound HTTP for udata, hardened against SSRF.

This is the junction between the udata-agnostic :mod:`udata.ssrf` module and
udata's configuration: :func:`ssrf_policy_for` is the one place where the
``URLS_ALLOW_*`` settings are turned into an :class:`~udata.ssrf.SSRFPolicy`.

Use :func:`ssrf_session` for **any** fetch of a URL that comes, directly or
indirectly, from user input — harvest sources, dataservice documentation, etc.
Trusted operator-configured integrations (metrics API, webhooks, OAuth
providers…) are not an SSRF vector and may legitimately target internal hosts;
they intentionally do not go through this guard.
"""

from __future__ import annotations

from collections.abc import Iterable

from flask import current_app

from udata.ssrf import SSRFPolicy, SSRFProtectedSession


def ssrf_policy_for(local: bool, private: bool, schemes: Iterable[str]) -> SSRFPolicy:
    """
    Map udata's ``URLS_ALLOW_*`` semantics onto an :class:`SSRFPolicy`.

    :func:`udata.uris.validate` applies this policy to the URLs users submit and
    :func:`ssrf_session` to the connections udata opens. Both go through here so
    they cannot drift apart — a URL accepted at input must not be refused at
    fetch time, and above all the reverse.
    """
    # udata.uris.validate groups link-local under "private", so URLS_ALLOW_PRIVATE
    # drives it here too. It has no notion of IETF-reserved ranges: mapping them
    # to that same toggle is a decision of this module, so that a deployment
    # opening up internal targets does not have to enumerate every category.
    return SSRFPolicy(
        allow_loopback=local,
        allow_private=private,
        allow_link_local=private,
        allow_reserved=private,
        allowed_schemes=frozenset(schemes),
    )


def ssrf_policy() -> SSRFPolicy:
    """Build an :class:`SSRFPolicy` from the current app's ``URLS_ALLOW_*`` config."""
    config = current_app.config
    return ssrf_policy_for(
        local=config["URLS_ALLOW_LOCAL"],
        private=config["URLS_ALLOW_PRIVATE"],
        schemes=config["URLS_ALLOWED_SCHEMES"],
    )


def ssrf_session() -> SSRFProtectedSession:
    """Return a :class:`SSRFProtectedSession` configured from the app settings."""
    return SSRFProtectedSession(ssrf_policy())
