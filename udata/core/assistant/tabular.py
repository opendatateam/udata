"""HTTP client for the api-tabular service (resource profiles and data).

Data is read through the declarative query-string API:
``GET /api/resources/<rid>/data/?<query>`` (filters, ``__groupby``,
aggregations, sorting, pagination).

``TabularRequestRefused`` carries api-tabular's status and error detail, which the
tools relay to the model as they are: api-tabular is a public API, its errors are
meant to be read. Other ``TabularError`` messages (network, timeout, invalid JSON)
stay in the logs, like the internal URLs.
"""

import logging

import requests
from flask import current_app

from udata.core.assistant.data_query import PAGE_SIZE
from udata.utils import normalize_uuid

log = logging.getLogger(__name__)

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
DATA_ROUTE = "/api/resources/{rid}/data/"

# Seconds; a hanging api-tabular call must not stall the agent's tool call.
TABULAR_TIMEOUT = 30
# Bound on the error detail fed back to the agent.
MAX_DETAIL_LENGTH = 300


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, invalid JSON, unconfigured).

    The message is meant for the logs and never contains the requested URL.
    """


class TabularRequestRefused(TabularError):
    """api-tabular answered with an error status, its detail in ``detail``."""

    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail[:MAX_DETAIL_LENGTH]
        super().__init__(f"{status}: {self.detail}")


def _error_detail(response: requests.Response) -> str:
    """Detail of api-tabular's ``errors[0]``: its text, or the ``message`` of the
    PostgREST error object it relays, else its title, else the plain-text body."""
    try:
        error = response.json()["errors"][0]
    except (ValueError, AttributeError, IndexError, KeyError, TypeError):
        return response.text.strip()
    detail = error.get("detail") if isinstance(error, dict) else None
    if isinstance(detail, dict):
        detail = detail.get("message")
    if isinstance(detail, str) and detail:
        return detail
    title = error.get("title") if isinstance(error, dict) else None
    return title if isinstance(title, str) else ""


def _validate_resource_id(resource_id: str) -> str:
    """Reject anything but a plain UUID before it reaches the URL path.

    The value is interpolated into request paths, so a malformed id must be
    stopped here rather than smuggled into the upstream URL (path traversal,
    query injection through ``?`` or ``#``).
    """
    if (normalized := normalize_uuid(resource_id)) is None:
        raise TabularError("invalid resource_id: a UUID is expected.")
    return normalized


class TabularClient:
    def __init__(self):
        base_url = current_app.config["TABULAR_API_URL"]
        # A trailing slash would double the one the routes start with.
        self.base_url = base_url.rstrip("/") if base_url else base_url

    def get_profile(self, resource_id: str) -> dict:
        return self._request(PROFILE_ROUTE.format(rid=_validate_resource_id(resource_id)))

    def get_data(self, resource_id: str, query: str) -> dict:
        """Fetch ``/data/`` with an already URL-encoded query string, sent verbatim.

        The URL is built by concatenation, never through ``params=``, so that
        pre-encoded (possibly double-encoded) parts are not re-encoded.
        """
        return self._request(f"{DATA_ROUTE.format(rid=_validate_resource_id(resource_id))}?{query}")

    def _request(self, route: str) -> dict:
        """JSON of an api-tabular GET."""
        if not self.base_url:
            log.warning("api-tabular is not configured (TABULAR_API_URL is not set)")
            raise TabularError("api-tabular is not configured (TABULAR_API_URL is not set)")
        url = f"{self.base_url}{route}"
        try:
            response = requests.get(url, timeout=TABULAR_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            raise TabularRequestRefused(
                error.response.status_code, _error_detail(error.response)
            ) from error
        except requests.exceptions.RequestException as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            raise TabularError("the tabular service returned an error.") from error


def has_more_rows(first_page: dict) -> bool:
    """Whether the query of ``first_page``, its page 1 of PAGE_SIZE, matches more rows.

    A raw query has an exact ``meta.total``. An aggregated one has none, but api-tabular
    links its page to a next one only when that next page has rows.
    """
    rows = first_page.get("data") if isinstance(first_page, dict) else None
    if not isinstance(rows, list) or len(rows) < PAGE_SIZE:
        return False
    meta = first_page.get("meta")
    total = meta.get("total") if isinstance(meta, dict) else None
    if isinstance(total, int):
        return total > PAGE_SIZE
    links = first_page.get("links")
    return isinstance(links, dict) and bool(links.get("next"))
