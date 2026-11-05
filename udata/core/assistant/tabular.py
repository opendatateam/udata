"""HTTP client for the api-tabular service (resource profiles and read-only SQL).

The SQL execution contract is hypothetical (see ``execute_sql``); adjust the
route and payload once the api-tabular contract is specified.

``TabularError`` messages reach tool outputs and client responses, so they
are sanitized: internal URLs and upstream details are logged server-side.
"""

import logging
import uuid

import requests
from flask import current_app

log = logging.getLogger(__name__)

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
SQL_ROUTE = "/api/resources/{rid}/sql"

# Hard bound: this client feeds an LLM agent tool call, so a hanging request
# must not stall indefinitely when ``requests`` is given ``timeout=None``.
DEFAULT_TIMEOUT = 30
# Default timeout (seconds) for api-tabular calls; overridable per client.
TABULAR_SQL_TIMEOUT = 30


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, invalid JSON, unconfigured).

    The message is safe to show to clients and to feed back to the agent:
    it never contains the requested URL or upstream response details.
    """


def _validate_resource_id(resource_id: str) -> str:
    """Reject anything but a plain UUID before it reaches the URL path.

    The value is interpolated into request paths, so a malformed id must be
    stopped here rather than smuggled into the upstream URL (path traversal,
    query injection through ``?`` or ``#``).
    """
    try:
        parsed = uuid.UUID(resource_id)
    except (ValueError, AttributeError, TypeError):
        raise TabularError("resource_id invalide : un UUID est attendu.") from None
    return str(parsed)


class TabularClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = base_url if base_url is not None else current_app.config["TABULAR_SQL_URL"]
        self.timeout = self._resolve_timeout(timeout)

    @staticmethod
    def _resolve_timeout(timeout: int | None) -> int:
        if timeout is None:
            timeout = TABULAR_SQL_TIMEOUT
        if not timeout or timeout <= 0:
            return DEFAULT_TIMEOUT
        return timeout

    def get_profile(self, resource_id: str) -> dict:
        return self._request("GET", PROFILE_ROUTE.format(rid=_validate_resource_id(resource_id)))

    def execute_sql(self, resource_id: str, sql: str) -> dict:
        return self._request(
            "POST", SQL_ROUTE.format(rid=_validate_resource_id(resource_id)), json={"query": sql}
        )

    def _request(self, method: str, route: str, **kwargs) -> dict:
        if not self.base_url:
            raise TabularError("api-tabular is not configured (TABULAR_SQL_URL is not set)")
        url = f"{self.base_url}{route}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            log.warning("api-tabular request failed: %s %s: %s", method, url, error)
            raise TabularError("le service tabulaire a renvoyé une erreur.") from error
        except ValueError as error:
            log.warning("api-tabular returned invalid JSON: %s %s: %s", method, url, error)
            raise TabularError("le service tabulaire a renvoyé une réponse invalide.") from error
