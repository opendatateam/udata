"""HTTP client for the api-tabular service (resource profiles and data).

Data is read through the declarative query-string API:
``GET /api/resources/<rid>/data/?<query>`` (filters, ``__groupby``,
aggregations, sorting, pagination).

``TabularError`` messages are never shown to clients nor to the model: the
tools translate each error into their own French message, keeping only the
refusal detail of ``TabularRequestRefused``. Internal URLs and upstream
details stay in the logs.
"""

import ast
import logging
import re

import requests
from flask import current_app

from udata.core.assistant.data_query import PAGE_SIZE, with_page
from udata.utils import normalize_uuid

log = logging.getLogger(__name__)

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
DATA_ROUTE = "/api/resources/{rid}/data/"

# Seconds; a hanging api-tabular call must not stall the agent's tool call.
TABULAR_TIMEOUT = 30


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, invalid JSON, unconfigured).

    The message is meant for the logs and never contains the requested URL.
    """


class TabularRequestRefused(TabularError):
    """api-tabular refused the query, with the part at fault in ``detail``.

    The detail only quotes the query the agent wrote, or the database error
    it caused, so it is fed back to the agent to let it fix the query.
    """

    def __init__(self, detail: str):
        self.detail = detail[:MAX_DETAIL_LENGTH]
        super().__init__(self.detail)


class TabularResourceUnavailable(TabularError):
    """api-tabular does not serve the resource: a 404 without a refusal detail, or its table is missing."""


# Bound on the refusal detail fed back to the agent.
MAX_DETAIL_LENGTH = 300

FORBIDDEN_AGGREGATION = "agrégation non autorisée sur cette ressource"
# api-tabular's two "Unauthorized parameters" details (build_sql_query_string, raise_if_not_index).
FORBIDDEN_AGGREGATION_DETAIL = re.compile(r"^Aggregation parameters .* are not allowed")
NOT_INDEXED_DETAIL = re.compile(
    r"^(?P<column>.*) is not among the allowed columns: (?P<allowed>\{.*\})$", re.S
)
# The resource's table is gone: the resource is not available, not the query wrong.
MISSING_TABLE_CODES = {"42P01", "PGRST205"}
# The resource's internal table name, possibly schema-qualified, read as "ressource".
TABLE_NAME = re.compile(r"\b(?:csvapi\.)?[0-9a-f]{32}\b")


def _first_error(response: requests.Response) -> tuple[object, object] | None:
    """``title`` and ``detail`` of api-tabular's ``errors[0]``, None if the body has none."""
    try:
        error = response.json()["errors"][0]
        return error.get("title"), error.get("detail")
    except (ValueError, AttributeError, IndexError, KeyError, TypeError):
        return None


def _is_missing_table(response: requests.Response) -> bool:
    """A "Database error" saying the resource's table is gone, whatever its status."""
    error = _first_error(response)
    detail = error[1] if error else None
    return isinstance(detail, dict) and detail.get("code") in MISSING_TABLE_CODES


def _refusal_detail(response: requests.Response) -> str | None:
    """What the agent can fix in a refused query, from api-tabular's ``errors[0]``.

    A 400 of api-tabular's own parser carries a text detail; a "Database error"
    (400 or 404) relays PostgREST's error object, whose ``message`` is kept.
    A plain-text 404 is api-tabular not knowing the resource: no detail.
    """
    if (error := _first_error(response)) is None:
        return None
    title, detail = error
    status = response.status_code
    if status == 403:
        return _unauthorized_detail(detail) if title == "Unauthorized parameters" else None
    if isinstance(detail, dict) and status in (400, 404):
        if detail.get("code") in MISSING_TABLE_CODES:
            return None
        detail = detail.get("message")
    elif status != 400:
        return None
    if not isinstance(detail, str) or not detail:
        return None
    return TABLE_NAME.sub("ressource", detail)


def _unauthorized_detail(detail) -> str | None:
    """A forbidden aggregation, or a column outside the indexes of a large resource."""
    if not isinstance(detail, str):
        return None
    if FORBIDDEN_AGGREGATION_DETAIL.match(detail):
        return FORBIDDEN_AGGREGATION
    if not (match := NOT_INDEXED_DETAIL.match(detail)):
        return None
    try:
        allowed = ", ".join(sorted(ast.literal_eval(match["allowed"])))
    except (ValueError, SyntaxError, TypeError):
        allowed = match["allowed"]
    return (
        f"colonne {match['column']} non indexée : seules les colonnes {allowed} "
        "peuvent être regroupées ou agrégées"
    )


def _validate_resource_id(resource_id: str) -> str:
    """Reject anything but a plain UUID before it reaches the URL path.

    The value is interpolated into request paths, so a malformed id must be
    stopped here rather than smuggled into the upstream URL (path traversal,
    query injection through ``?`` or ``#``).
    """
    if (normalized := normalize_uuid(resource_id)) is None:
        raise TabularError("resource_id invalide : un UUID est attendu.")
    return normalized


def _data_route(resource_id: str, query: str) -> str:
    return f"{DATA_ROUTE.format(rid=_validate_resource_id(resource_id))}?{query}"


class TabularClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url if base_url is not None else current_app.config["TABULAR_API_URL"]

    def get_profile(self, resource_id: str) -> dict:
        return self._request(PROFILE_ROUTE.format(rid=_validate_resource_id(resource_id)))

    def get_data(self, resource_id: str, query: str) -> dict:
        """Fetch ``/data/`` with an already URL-encoded query string, sent verbatim.

        The URL is built by concatenation, never through ``params=``, so that
        pre-encoded (possibly double-encoded) parts are not re-encoded.
        """
        return self._request(_data_route(resource_id, query))

    def has_more_rows(self, resource_id: str, query: str, first_page: dict) -> bool:
        """Whether ``query`` matches more rows than ``first_page``, its page 1 of PAGE_SIZE.

        A raw query has an exact ``meta.total``. An aggregated one has none: a missing
        ``links.next`` ends it, otherwise page 51 is probed: api-tabular 0.4 links every full
        page to a next one. PostgREST answers 416 beyond the last row.
        """
        rows = first_page.get("data") if isinstance(first_page, dict) else None
        if not isinstance(rows, list) or len(rows) < PAGE_SIZE:
            return False
        meta = first_page.get("meta")
        total = meta.get("total") if isinstance(meta, dict) else None
        if isinstance(total, int):
            return total > PAGE_SIZE
        links = first_page.get("links")
        if not isinstance(links, dict) or not links.get("next"):
            return False
        probe = self._request(
            _data_route(resource_id, with_page(query, page=PAGE_SIZE + 1, page_size=1)),
            out_of_range_ok=True,
        )
        return bool(probe.get("data")) if isinstance(probe, dict) else False

    def _request(self, route: str, out_of_range_ok: bool = False) -> dict:
        """JSON of an api-tabular GET; with ``out_of_range_ok``, a 416 is an empty dict."""
        if not self.base_url:
            log.warning("api-tabular is not configured (TABULAR_API_URL is not set)")
            raise TabularError("api-tabular is not configured (TABULAR_API_URL is not set)")
        url = f"{self.base_url}{route}"
        try:
            response = requests.get(url, timeout=TABULAR_TIMEOUT)
            if out_of_range_ok and response.status_code == 416:
                return {}
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            status = error.response.status_code if error.response is not None else None
            if error.response is not None and (detail := _refusal_detail(error.response)):
                raise TabularRequestRefused(detail) from error
            if status == 404 or (error.response is not None and _is_missing_table(error.response)):
                raise TabularResourceUnavailable(
                    "la ressource n'est pas disponible dans le service tabulaire."
                ) from error
            raise TabularError("le service tabulaire a renvoyé une erreur.") from error
        except requests.exceptions.RequestException as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            raise TabularError("le service tabulaire a renvoyé une erreur.") from error
        except ValueError as error:
            log.warning("api-tabular returned invalid JSON: %s: %s", url, error)
            raise TabularError("le service tabulaire a renvoyé une réponse invalide.") from error
