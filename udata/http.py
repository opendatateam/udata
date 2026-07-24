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

import requests

from udata import uris
from udata.utils import raise_if_redirect


def head(url, headers={}, **kwargs):
    kwargs["allow_redirects"] = kwargs.get("allow_redirects", False)
    uris.validate(url)
    response = requests.head(url, headers=headers, **kwargs)
    if not kwargs["allow_redirects"]:
        raise_if_redirect(response)
    return response


def get(url, headers={}, **kwargs):
    kwargs["allow_redirects"] = kwargs.get("allow_redirects", False)
    uris.validate(url)
    response = requests.get(url, headers=headers, **kwargs)
    if not kwargs["allow_redirects"]:
        raise_if_redirect(response)
    return response


def post(url, data, headers={}, **kwargs):
    kwargs["allow_redirects"] = kwargs.get("allow_redirects", False)
    uris.validate(url)
    response = requests.post(url, data=data, headers=headers, **kwargs)
    if not kwargs["allow_redirects"]:
        raise_if_redirect(response)
    return response
