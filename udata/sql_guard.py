"""Read-only guard for SQL statements executed against the tabular engine.

Parser-based allow-list (sqlglot, DuckDB dialect — the api-tabular engine):
exactly one statement, root Select/Union/Intersect/Except/Values, no write
or lock nodes anywhere (including inside CTE
bodies), an explicit function allow-list, and table sources restricted to
plain identifiers.

This is defense in depth on top of executor-side controls: the api-tabular
service must still run queries under a read-only role, with external-access
restrictions, a statement timeout and a row limit. Those live in the
api-tabular deployment, not in this repository.
"""

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

__all__ = ["UnsafeSQLError", "assert_read_only"]

# api-tabular runs DuckDB; parsing with the matching dialect keeps quoted
# identifiers and engine-specific syntax unambiguous.
DIALECT = "duckdb"

_WRITE_NODES = (
    exp.Alter,
    exp.Commit,
    exp.Copy,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Lock,
    exp.Merge,
    exp.Transaction,
    exp.Update,
    exp.Into,
)

# Statement types allowed at the root (CTE bodies are validated recursively).
# UNION/INTERSECT/EXCEPT set operations stay read-only.
_ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.Values)

# DuckDB built-ins the assistant legitimately uses. Anything else — including
# every file reader, admin and session function — is rejected by default.
# Deliberately excluded as resource-amplification or non-deterministic
# vectors: generate_series/range/sequence, random, hashing (md5/hash),
# unbounded-output builders (repeat, lpad, rpad, printf, format), regex
# functions (ReDoS), quadratic string-similarity functions, and binary
# codecs (encode/decode/to_binary/from_binary).
_ALLOWED_FUNCTIONS = frozenset(
    name.upper()
    for name in (
        # aggregates
        "avg",
        "count",
        "sum",
        "min",
        "max",
        "median",
        "stddev",
        "stddev_pop",
        "stddev_samp",
        "variance",
        "var_pop",
        "var_samp",
        "string_agg",
        "group_concat",
        "list_agg",
        "arg_min",
        "arg_max",
        "first",
        "last",
        "approx_count_distinct",
        "quantile",
        "quantile_cont",
        "quantile_disc",
        # math
        "abs",
        "round",
        "ceil",
        "ceiling",
        "floor",
        "trunc",
        "sqrt",
        "cbrt",
        "exp",
        "ln",
        "log",
        "log10",
        "log2",
        "power",
        "pow",
        "mod",
        "pi",
        "sign",
        "gcd",
        "lcm",
        "degrees",
        "radians",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "atan2",
        # strings
        "upper",
        "lower",
        "length",
        "char_length",
        "character_length",
        "substring",
        "substr",
        "trim",
        "ltrim",
        "rtrim",
        "btrim",
        "replace",
        "concat",
        "concat_ws",
        "left",
        "right",
        "reverse",
        "initcap",
        "starts_with",
        "contains",
        "strpos",
        "position",
        "split_part",
        "ascii",
        "chr",
        "soundex",
        # dates and times
        "date",
        "time",
        "timestamp",
        "interval",
        "date_trunc",
        "date_part",
        "timestamp_trunc",
        "datepart",
        "datediff",
        "date_diff",
        "dateadd",
        "date_add",
        "extract",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "quarter",
        "dayofweek",
        "day_of_week",
        "dayofyear",
        "day_of_year",
        "week",
        "isodow",
        "epoch",
        "age",
        "now",
        "current_date",
        "current_time",
        "current_timestamp",
        "current_localtimestamp",
        "localtime",
        "last_day",
        "make_date",
        "make_time",
        "make_timestamp",
        "strftime",
        "strptime",
        "to_date",
        "to_time",
        "to_timestamp",
        "timezone",
        "date_bin",
        "date_slice",
        # conditionals and coalescing
        "coalesce",
        "ifnull",
        "nullif",
        "if",
        "nvl",
        "greatest",
        "least",
        "case",
        "cast",
        "try_cast",
        # structural (lists/structs/maps/rows, unnest)
        "unnest",
        "array",
        "list",
        "list_value",
        "struct",
        "struct_pack",
        "row",
        "map",
        "map_from_entries",
        "cardinality",
        "list_length",
        "array_length",
        "list_concat",
        "array_concat",
        "list_contains",
        "array_contains",
        "list_extract",
        "array_extract",
        "array_slice",
        "list_slice",
        "list_transform",
        "list_filter",
        "list_aggregate",
        "list_sort",
        "list_reverse_sort",
        "list_distinct",
        "flatten",
        "list_has",
        "list_has_all",
        "list_has_any",
        "element_at",
        # identifier helpers
        "uuid",
        "gen_random_uuid",
        # window and ranking
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
        "percentile",
        "percentile_cont",
        "percentile_disc",
        # type introspection
        "typeof",
        "isnan",
        "isinf",
        "isfinite",
        # geo helpers sometimes present in open data
        "st_x",
        "st_y",
        "st_point",
        "st_distance",
        "st_transform",
        "st_geomfromtext",
        "st_as_text",
        "st_intersects",
        "st_within",
        "st_area",
        "st_length",
    )
)

# Raw-text scan for single-quoted literals, on purpose: a literal mixing a
# doubled-quote escape ('') and a semicolon is where sqlglot and DuckDB
# could disagree on where the string ends — and a second statement hidden
# behind that ambiguity would bypass the one-statement check below.
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")


class UnsafeSQLError(ValueError):
    """Raised when a SQL statement is not guaranteed to be read-only."""


def _function_name(node: exp.Func | exp.Anonymous) -> str:
    """Canonical uppercase function name, robust to quoting and dialect aliases."""
    if isinstance(node, exp.Anonymous):
        # Anonymous nodes carry the raw (possibly quoted) name in ``this``.
        name = node.name
    else:
        name = node.sql_name()
    return name.upper()


def _check_functions(tree: exp.Expression) -> None:
    for node in tree.find_all((exp.Func, exp.Anonymous)):
        if _function_name(node) not in _ALLOWED_FUNCTIONS:
            raise UnsafeSQLError(f"Function is not allowed: {_function_name(node)}")


def _check_tables(tree: exp.Expression) -> None:
    """Table sources must be plain identifiers: no function scans, no string
    literals (DuckDB resolves them as file paths), no quoted table names."""
    for node in tree.find_all(exp.Table):
        if node.this is not None and not isinstance(node.this, exp.Identifier):
            raise UnsafeSQLError(
                f"Table source is not a plain identifier: {node.sql(dialect=DIALECT)}"
            )
        if node.this is not None and node.this.args.get("quoted"):
            raise UnsafeSQLError(
                f"Quoted table identifiers are not allowed: {node.sql(dialect=DIALECT)}"
            )
        if node.args.get("db") is not None:
            raise UnsafeSQLError(
                f"Qualified table names are not allowed: {node.sql(dialect=DIALECT)}"
            )


def _check_string_literals(sql: str) -> None:
    for match in _STRING_LITERAL_RE.finditer(sql):
        literal = match.group(0)
        if "''" in literal and ";" in literal:
            raise UnsafeSQLError("Ambiguous escaped quote near semicolon in string literal")


def _check_no_writes(tree: exp.Expression) -> None:
    for node_type in _WRITE_NODES:
        for node in tree.find_all(node_type):
            raise UnsafeSQLError(
                f"Statement contains a disallowed construct: "
                f"{type(node).__name__} ({node.sql(dialect=DIALECT)[:80]})"
            )


def _check_query(tree: exp.Expression) -> None:
    _check_no_writes(tree)
    _check_functions(tree)
    _check_tables(tree)


def _parse_single(sql: str) -> exp.Expression:
    try:
        return sqlglot.parse_one(sql, dialect=DIALECT)
    except SqlglotError as error:
        raise UnsafeSQLError(f"SQL could not be parsed: {error}") from error


def assert_read_only(sql: str) -> None:
    """Raise UnsafeSQLError unless sql is a single read-only statement."""
    _check_string_literals(sql)
    try:
        statements = sqlglot.parse(sql, dialect=DIALECT)
    except SqlglotError as error:
        raise UnsafeSQLError(f"SQL could not be parsed: {error}") from error
    statements = [statement for statement in statements if statement is not None]
    if len(statements) != 1:
        raise UnsafeSQLError("Exactly one SQL statement is required")
    tree = statements[0]
    if isinstance(tree, exp.Command):
        raise UnsafeSQLError(f"Statement type is not allowed: {tree.this}")
    if not isinstance(tree, _ALLOWED_ROOTS):
        raise UnsafeSQLError(f"Statement type is not allowed: {type(tree).__name__}")
    _check_query(tree)
