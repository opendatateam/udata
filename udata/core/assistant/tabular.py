"""HTTP client for the api-tabular service (resource profiles and data).

Data is read through the declarative query-string API:
``GET /api/resources/<rid>/data/?<query>`` (filters, ``__groupby``,
aggregations, sorting, pagination).

``TabularRequestRefused`` carries api-tabular's status and error detail, which the
tools relay to the model as they are: api-tabular is a public API, its errors are
meant to be read. ``TabularUnexpectedAnswer`` is an answer the models below cannot
read. Other ``TabularError`` messages (network, timeout, unconfigured) stay in the
logs, like the internal URLs.
"""

import logging
from typing import Any, TypeVar
from uuid import UUID

import requests
from flask import current_app
from pydantic import BaseModel, ValidationError

from udata.core.assistant.data_query import PAGE_SIZE

log = logging.getLogger(__name__)

PROFILE_ROUTE = "/api/resources/{rid}/profile/"
DATA_ROUTE = "/api/resources/{rid}/data/"

ModelT = TypeVar("ModelT", bound=BaseModel)

# Seconds; a hanging api-tabular call must not stall the agent's tool call.
TABULAR_TIMEOUT = 30
# Bound on the error detail fed back to the agent.
MAX_DETAIL_LENGTH = 300


class TabularColumn(BaseModel):
    # A column without type is left out of `columns()`, not the whole profile.
    python_type: str | None = None


class TabularProfileDetails(BaseModel):
    header: list[str] | None = None
    columns: dict[str, TabularColumn]
    # csv-detective leaves it out for large files.
    total_lines: int | None = None


class TabularProfile(BaseModel):
    """api-tabular's `/profile/` answer, as far as the assistant reads it."""

    profile: TabularProfileDetails

    def columns(self) -> dict[str, str]:
        """`{name: python_type}`, in `header` order."""
        columns = self.profile.columns
        names = self.profile.header if self.profile.header is not None else list(columns)
        return {
            name: python_type
            for name in names
            if name in columns and (python_type := columns[name].python_type) is not None
        }


class TabularMeta(BaseModel):
    # Not given for an aggregation.
    total: int | None = None


class TabularLinks(BaseModel):
    next: str | None = None


class TabularPage(BaseModel):
    """A page of api-tabular's `/data/` answer."""

    data: list[dict[str, Any]]
    meta: TabularMeta = TabularMeta()
    links: TabularLinks = TabularLinks()


class TabularError(RuntimeError):
    """Raised on any api-tabular failure (HTTP error, timeout, unexpected answer, unconfigured).

    The message is meant for the logs and never contains the requested URL.
    """


class TabularUnexpectedAnswer(TabularError):
    """api-tabular answered, but not in the shape the models read (invalid JSON included)."""


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


class TabularClient:
    def __init__(self):
        base_url = current_app.config["TABULAR_API_URL"]
        # A trailing slash would double the one the routes start with.
        self.base_url = base_url.rstrip("/") if base_url else base_url

    def get_profile(self, resource_id: UUID) -> TabularProfile:
        return self._request(PROFILE_ROUTE.format(rid=resource_id), TabularProfile)

    def get_data(self, resource_id: UUID, query: str) -> TabularPage:
        """Fetch ``/data/`` with an already URL-encoded query string, sent verbatim.

        The URL is built by concatenation, never through ``params=``, so that
        pre-encoded (possibly double-encoded) parts are not re-encoded.
        """
        return self._request(f"{DATA_ROUTE.format(rid=resource_id)}?{query}", TabularPage)

    def _request(self, route: str, model: type[ModelT]) -> ModelT:
        """An api-tabular GET, read as `model`."""
        if not self.base_url:
            log.warning("api-tabular is not configured (TABULAR_API_URL is not set)")
            raise TabularError("api-tabular is not configured (TABULAR_API_URL is not set)")
        url = f"{self.base_url}{route}"
        try:
            response = requests.get(url, timeout=TABULAR_TIMEOUT)
            response.raise_for_status()
            return model.model_validate_json(response.content)
        except requests.exceptions.HTTPError as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            raise TabularRequestRefused(
                error.response.status_code, _error_detail(error.response)
            ) from error
        except requests.exceptions.RequestException as error:
            log.warning("api-tabular request failed: %s: %s", url, error)
            raise TabularError("the tabular service returned an error.") from error
        except ValidationError as error:
            log.warning("api-tabular answered an unexpected shape: %s: %s", url, error)
            raise TabularUnexpectedAnswer(
                "the tabular service returned an unexpected answer."
            ) from error


def has_more_rows(first_page: TabularPage) -> bool:
    """Whether the query of ``first_page``, its page 1 of PAGE_SIZE, matches more rows.

    A raw query has an exact ``meta.total``. An aggregated one has none, but api-tabular
    links its page to a next one only when that next page has rows.
    """
    if len(first_page.data) < PAGE_SIZE:
        return False
    if first_page.meta.total is not None:
        return first_page.meta.total > PAGE_SIZE
    return bool(first_page.links.next)
