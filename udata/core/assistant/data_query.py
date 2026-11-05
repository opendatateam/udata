"""Build api-tabular `/data/` query strings.

The grammar mirrors cdata's `buildFilterQuery` / `fetchTabularData`
(datagouv-components/src/functions/tabularApi.ts); `_encode` is the
equivalent of JavaScript's `encodeURIComponent`.
"""

from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

FilterCondition = Literal[
    "exact",
    "differs",
    "is_null",
    "is_not_null",
    "greater",
    "less",
    "strictly_greater",
    "strictly_less",
]
Aggregate = Literal["avg", "sum", "count", "min", "max"]
PAGE_SIZE = 50


class Filter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cls: Literal["Filter"] = Field("Filter", alias="_cls")
    column: str
    condition: FilterCondition
    value: str | None = None


class AndFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cls: Literal["AndFilters"] = Field("AndFilters", alias="_cls")
    filters: list["Filter | OrFilters"]


class OrFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cls: Literal["OrFilters"] = Field("OrFilters", alias="_cls")
    filters: list["Filter | AndFilters"]


AndFilters.model_rebuild()
OrFilters.model_rebuild()

GenericFilter = Annotated[Filter | AndFilters | OrFilters, Field(discriminator="cls")]


def _encode(value: str) -> str:
    return quote(value, safe="-_.!~*'()")


def _encode_condition_value(value: str) -> str:
    # The value is percent-decoded twice (query string, then the or()/and()
    # parser): grammar-significant characters must be double-encoded.
    return _encode(value).replace(".", "%252E").replace("(", "%2528").replace(")", "%2529")


def _null_condition(f: Filter) -> str | None:
    if f.condition == "is_null":
        return f"{_encode(f.column)}__isnull"
    if f.condition == "is_not_null":
        return f"{_encode(f.column)}__isnotnull"
    return None


def _param(f: Filter) -> str | None:
    if (null := _null_condition(f)) is not None:
        return null
    if not f.value:
        return None
    return f"{_encode(f.column)}__{_encode(f.condition)}={_encode(f.value)}"


def _condition(f: Filter) -> str | None:
    if (null := _null_condition(f)) is not None:
        return null
    if not f.value:
        return None
    return f"{_encode(f.column)}__{_encode(f.condition)}.{_encode_condition_value(f.value)}"


def _group(group: "AndFilters | OrFilters") -> str | None:
    operator = "or" if isinstance(group, OrFilters) else "and"
    parts = [
        _group(child) if isinstance(child, AndFilters | OrFilters) else _condition(child)
        for child in group.filters
    ]
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    return f"{operator}({','.join(parts)})"


def _build_filter_query(filters: GenericFilter) -> list[str]:
    params: list[str] = []
    if isinstance(filters, Filter):
        if (p := _param(filters)) is not None:
            params.append(p)
    elif isinstance(filters, AndFilters):
        for child in filters.filters:
            if isinstance(child, Filter):
                if (p := _param(child)) is not None:
                    params.append(p)
            elif (nested := _group(child)) is not None:
                params.append(f"or={nested[2:]}")
    elif (nested := _group(filters)) is not None:
        params.append(f"or={nested[2:]}")
    return params


def build_data_query(
    *,
    groupby: str | None = None,
    aggregate: tuple[str, Aggregate] | None = None,
    filters: GenericFilter | None = None,
    sort: tuple[str, Literal["asc", "desc"]] | None = None,
    columns: list[str] | None = None,
) -> str:
    """Query string for `/data/`, without `page` / `page_size` (see `with_page`)."""
    params: list[str] = []
    if columns:
        params.append("columns=" + ",".join(_encode(c) for c in columns))
    if groupby:
        params.append(f"{_encode(groupby)}__groupby")
    if aggregate:
        params.append(f"{_encode(aggregate[0])}__{_encode(aggregate[1])}")
    if sort:
        params.append(f"{_encode(sort[0])}__sort={_encode(sort[1])}")
    if filters:
        params.extend(_build_filter_query(filters))
    return "&".join(params)


def with_page(query: str, page: int = 1, page_size: int = PAGE_SIZE) -> str:
    paging = f"page={page}&page_size={page_size}"
    return f"{query}&{paging}" if query else paging


def filter_columns(filters: GenericFilter | None) -> set[str]:
    """Names of every column referenced by a filter tree."""
    if filters is None:
        return set()
    if isinstance(filters, Filter):
        return {filters.column}
    cols: set[str] = set()
    for child in filters.filters:
        cols |= filter_columns(child)
    return cols
