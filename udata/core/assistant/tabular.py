"""HTTP client for the api-tabular service (resource profiles and data).

Data is read through the declarative query-string API:
``GET /api/resources/<rid>/data/?<query>`` (filters, ``__groupby``,
aggregations, sorting, pagination).

``TabularError`` messages reach tool outputs and client responses, so they
are sanitized: internal URLs and upstream details are logged server-side.
"""

import logging
import uuid

import requests
from flask import current_app

log = logging.getLogger(__name__)

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
DATA_ROUTE = "/api/resources/{rid}/data/"

# Seconds; a hanging api-tabular call must not stall the agent's tool call.
TABULAR_TIMEOUT = 30


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, invalid JSON, unconfigured).

    The message is safe to show to clients and to feed back to the agent:
    it never contains the requested URL or upstream response details.
    """


class TabularRequestRefused(TabularError):
    """api-tabular refused the request (400), with the part at fault in ``detail``.

    The detail only quotes the query the agent wrote, so it is fed back to
    the agent to let it fix the query.
    """

    def __init__(self, detail: str):
        self.detail = detail[:MAX_DETAIL_LENGTH]
        super().__init__(f"requête refusée par le service tabulaire : {self.detail}")


# Bound on the refusal detail fed back to the agent.
MAX_DETAIL_LENGTH = 300


def _refusal_detail(response: requests.Response) -> str | None:
    """First ``errors[].detail`` of an api-tabular 400 body, if any."""
    try:
        errors = response.json().get("errors")
        detail = errors[0].get("detail")
    except (ValueError, AttributeError, IndexError, KeyError, TypeError):
        return None
    return detail if isinstance(detail, str) and detail else None


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
        self.base_url = base_url if base_url is not None else current_app.config["TABULAR_API_URL"]
        self.timeout = timeout if timeout and timeout > 0 else TABULAR_TIMEOUT

    def get_profile(self, resource_id: str) -> dict:
        return self._request("GET", PROFILE_ROUTE.format(rid=_validate_resource_id(resource_id)))

    def get_data(self, resource_id: str, query: str) -> dict:
        """Fetch ``/data/`` with an already URL-encoded query string, sent verbatim.

        The URL is built by concatenation, never through ``params=``, so that
        pre-encoded (possibly double-encoded) parts are not re-encoded.
        """
        route = DATA_ROUTE.format(rid=_validate_resource_id(resource_id))
        return self._request("GET", f"{route}?{query}")

    def has_more_groups(self, resource_id: str, query_without_page: str) -> bool:
        """Whether a 51st page of one group exists, i.e. more than 50 groups."""
        page = "page=51&page_size=1"
        query = f"{query_without_page}&{page}" if query_without_page else page
        payload = self.get_data(resource_id, query)
        return bool(payload.get("data")) if isinstance(payload, dict) else False

    def _request(self, method: str, route: str, **kwargs) -> dict:
        if not self.base_url:
            raise TabularError("api-tabular is not configured (TABULAR_API_URL is not set)")
        url = f"{self.base_url}{route}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            log.warning("api-tabular request failed: %s %s: %s", method, url, error)
            status = error.response.status_code if error.response is not None else None
            if status == 400 and (detail := _refusal_detail(error.response)):
                raise TabularRequestRefused(detail) from error
            if status == 404:
                raise TabularError(
                    "la ressource n'est pas disponible dans le service tabulaire."
                ) from error
            raise TabularError("le service tabulaire a renvoyé une erreur.") from error
        except requests.exceptions.RequestException as error:
            log.warning("api-tabular request failed: %s %s: %s", method, url, error)
            raise TabularError("le service tabulaire a renvoyé une erreur.") from error
        except ValueError as error:
            log.warning("api-tabular returned invalid JSON: %s %s: %s", method, url, error)
            raise TabularError("le service tabulaire a renvoyé une réponse invalide.") from error
