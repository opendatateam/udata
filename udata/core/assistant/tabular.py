"""HTTP client for the api-tabular service (resource profiles and read-only SQL).

The SQL execution contract is hypothetical: ``POST {base}/api/resources/{rid}/sql``
with body ``{"query": sql}`` returning ``{"columns": [...], "rows": [[...]]}``.
Adjust ``execute_sql`` (route and payload) when the api-tabular contract is
specified. Routes are built in ``_request`` to keep them easy to change.
"""

import requests
from flask import current_app

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
SQL_ROUTE = "/api/resources/{rid}/sql"


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, invalid JSON, unconfigured)."""


class TabularClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = base_url if base_url is not None else current_app.config["TABULAR_SQL_URL"]
        self.timeout = timeout if timeout is not None else current_app.config["TABULAR_SQL_TIMEOUT"]

    def get_profile(self, resource_id: str) -> dict:
        return self._request("GET", PROFILE_ROUTE.format(rid=resource_id))

    def execute_sql(self, resource_id: str, sql: str) -> dict:
        return self._request("POST", SQL_ROUTE.format(rid=resource_id), json={"query": sql})

    def _request(self, method: str, route: str, **kwargs) -> dict:
        if not self.base_url:
            raise TabularError("api-tabular is not configured (TABULAR_SQL_URL is not set)")
        try:
            response = requests.request(
                method, f"{self.base_url}{route}", timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            raise TabularError(f"api-tabular request failed: {error}") from error
        except ValueError as error:
            raise TabularError(f"api-tabular returned invalid JSON: {error}") from error
