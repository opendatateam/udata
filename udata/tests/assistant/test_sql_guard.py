import pytest

from udata.sql_guard import _ALLOWED_FUNCTIONS, UnsafeSQLError, assert_read_only


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT a, b FROM data",
        "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
        "SELECT ';' AS semi",  # point-virgule dans une chaîne : OK
        "SELECT a FROM data -- ; comment\n",
        'SELECT "drop" FROM data',  # mot-clé en identifiant quoté : OK
        "SELECT 1;",  # point-virgule terminal unique : OK
        "SELECT count('x') FROM data",
        "SELECT upper('abc')",
        "SELECT date('2024-01-01')",
        "SELECT concat('a', 'b')",
        # unions and CTEs, including recursive ones
        "SELECT a FROM data UNION ALL SELECT b FROM data",
        "SELECT a FROM data UNION SELECT b FROM data INTERSECT SELECT c FROM data",
        "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM x) SELECT * FROM x",
        "WITH x(a, b) AS (SELECT 1, 2) SELECT * FROM x",
        # values and subqueries
        "VALUES (1, 2)",
        "SELECT * FROM (SELECT a FROM data) sub",
        # window functions and common built-ins
        "SELECT row_number() OVER (PARTITION BY g ORDER BY x) FROM data",
        "SELECT substring(trim(name), 1, 3) AS s FROM data",
        "SELECT date_trunc('month', d) AS m, sum(v) FROM data GROUP BY m ORDER BY m",
        "SELECT CAST(x AS INT), x::INT, TRY_CAST(x AS INT) FROM data",
        "SELECT coalesce(a, 0), nullif(a, b) FROM data",
        # unnest of a list column, as documented in the SQL prompt
        "SELECT items.value FROM data, UNNEST(list_col) AS items(value)",
        # the data table, quoted or not, with any case and alias
        'SELECT * FROM "data"',
        "SELECT d.a FROM DATA AS d",
        "SELECT * FROM data JOIN data AS other ON data.a = other.a",
        # DuckDB names sqlglot maps to differently named nodes
        "SELECT strftime(\"date\", '%Y') AS y, count(*) FROM data GROUP BY y",
        "SELECT strptime(d, '%d/%m/%Y') FROM data",
        "SELECT unnest(l) FROM data",
        "SELECT strpos(s, 'a'), position('a' IN s) FROM data",
        "SELECT epoch(d), to_timestamp(n), isodow(d) FROM data",
        "SELECT approx_count_distinct(a), array_agg(a), var_pop(n) FROM data",
        "SELECT array_length(l), list_sort(l), isnan(n), isinf(n) FROM data",
        "SELECT CASE WHEN a > 1 THEN 'x' ELSE 'y' END FROM data",
        "SELECT a % 2, mod(a, 2), d + INTERVAL 1 DAY FROM data",
    ],
)
def test_accepts_read_only(sql):
    assert_read_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE data",
        "SELECT 1; DROP TABLE data",
        "INSERT INTO t VALUES (1)",
        "WITH x AS (SELECT 1) DELETE FROM t",
        "WITH x AS (DELETE FROM t RETURNING *) SELECT count(*) FROM x",
        # file readers and table scans, quoted or not
        "SELECT read_parquet('/etc/passwd')",
        "SELECT read_csv('/etc/passwd')",
        "SELECT \"read_csv\"('/etc/passwd')",
        "SELECT read_csv_auto('/etc/passwd')",
        "SELECT read_ndjson('/tmp/x.ndjson')",
        "SELECT read_xlsx('/tmp/x.xlsx')",
        "SELECT read_text('/etc/passwd')",
        "SELECT read_json('/etc/passwd')",
        "SELECT * FROM glob('*')",
        "SELECT delta_scan('/tmp/delta')",
        "SELECT sqlite_scan('/tmp/x.db')",
        "SELECT postgres_scan('host=...')",
        # string-literal and function table sources
        "SELECT * FROM '/etc/passwd'",
        'SELECT * FROM "/etc/passwd"',
        'SELECT * FROM "data.csv"',
        'WITH "x.csv" AS (SELECT 1) SELECT * FROM "x.csv"',
        # catalog views and any table other than data or a CTE
        "SELECT * FROM duckdb_settings",
        "SELECT * FROM duckdb_tables",
        "SELECT * FROM pg_tables",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM other_table",
        "SELECT * FROM data.csv",
        "SELECT * FROM read_parquet('/etc/passwd')",
        # session/admin functions
        "SELECT set_config('a', 'b', false)",
        "SELECT \"set_config\"('a', 'b', false)",
        "SELECT pg_sleep(10)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT \"pg_read_file\"('/etc/passwd')",
        "SELECT pg_read_server_files('/etc/passwd')",
        "SELECT pg_read_binary_file('/etc/passwd')",
        "SELECT pg_ls_dir('.')",
        "SELECT pg_ls_waldir()",
        "SELECT lo_import('/etc/passwd')",
        "SELECT lo_from_bytea(0, '\\x00')",
        "SELECT setval('seq', 42)",
        "SELECT nextval('seq')",
        "SELECT pg_terminate_backend(123)",
        "SELECT pg_cancel_backend(123)",
        "SELECT pg_reload_conf()",
        "SELECT pg_advisory_lock(1)",
        "SELECT pg_stat_file('/etc/passwd')",
        # statements and engine commands
        "SET search_path TO public",
        "RESET search_path",
        "COMMENT ON TABLE t IS 'x'",
        "VACUUM t",
        "ANALYZE t",
        "ANALYSE t",
        "PREPARE p AS DELETE FROM t",
        "EXECUTE p",
        "LOCK TABLE t IN ACCESS EXCLUSIVE MODE",
        "COPY t FROM 'x'",
        "CREATE TABLE t (a INT)",
        "ALTER TABLE t ADD COLUMN b INT",
        "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET x = 1",
        "CALL my_proc()",
        "BEGIN",
        "COMMIT",
        "INSTALL httpfs",
        "LOAD httpfs",
        "DETACH DATABASE db",
        "EXPORT DATABASE 'dir'",
        "IMPORT DATABASE 'dir'",
        "CHECKPOINT",
        "USE my_db",
        "SHOW TABLES",
        "TABLE t",
        # locking and into clauses
        "SELECT * FROM t FOR UPDATE",
        "SELECT * FROM t FOR SHARE",
        "SELECT * FROM t FOR NO KEY UPDATE",
        "SELECT * INTO newtab FROM data",
        # EXPLAIN is rejected entirely (EXPLAIN ANALYZE executes the statement)
        "EXPLAIN SELECT * FROM t",
        "EXPLAIN (COSTS FALSE) SELECT * FROM t",
        "EXPLAIN WITH x AS (SELECT 1) SELECT * FROM x",
        "EXPLAIN ANALYZE DELETE FROM t",
        "EXPLAIN (ANALYZE) DELETE FROM t",
        "EXPLAIN (ANALYZE, COSTS OFF) DELETE FROM t",
        "EXPLAIN ANALYSE DELETE FROM t",
        "EXPLAIN INSERT INTO t VALUES (1)",
        "EXPLAIN INSTALL httpfs",
        # empty or unparseable
        "",
        "   \n\t ",
        "SELECT 'unterminated",
        "/* unterminated comment",
        "SELECT \\'; DROP TABLE t; --'",
        "SELECT 'a''; DROP TABLE t; --'",
    ],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        assert_read_only(sql)


@pytest.mark.parametrize("name", sorted(_ALLOWED_FUNCTIONS))
def test_every_allowed_function_passes(name):
    """Each allow-listed DuckDB name is accepted in its plain call form."""
    for args in ("x", "x, y", "x, y, z", ""):
        try:
            assert_read_only(f"SELECT {name}({args}) FROM data")
        except UnsafeSQLError as error:
            if "Function is not allowed" in str(error):
                raise
            continue
        return
    pytest.fail(f"{name} could not be parsed in any call form")
