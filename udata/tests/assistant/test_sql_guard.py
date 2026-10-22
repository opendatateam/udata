import pytest

from udata.core.assistant.sql_guard import UnsafeSQLError, assert_read_only


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT a, b FROM data",
        "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
        "SELECT ';' AS semi",  # point-virgule dans une chaîne : OK
        "SELECT a FROM t -- ; comment\n",
        'SELECT "drop" FROM t',  # mot-clé en identifiant quoté : OK
        "SELECT 1;",  # point-virgule terminal unique : OK
        "SELECT count('x') FROM t",
        "SELECT upper('abc')",
        "SELECT date('2024-01-01')",
        "SELECT concat('a', 'b')",
        "EXPLAIN SELECT * FROM t",
        "EXPLAIN (COSTS FALSE) SELECT * FROM t",
        "EXPLAIN WITH x AS (SELECT 1) SELECT * FROM x",
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
        "SELECT read_parquet('/etc/passwd')",
        "SELECT * FROM glob('*')",
        # finding 1: backslash in string must not over-blank the rest
        "SELECT '\\'; DROP TABLE t; --'",
        # finding 2: data-modifying CTE body
        "WITH x AS (DELETE FROM t RETURNING *) SELECT count(*) FROM x",
        # finding 3: nested parens in CTE body
        "WITH x AS (SELECT f(1)) DELETE FROM t",
        # finding 4: WITH RECURSIVE / column-list CTEs
        "WITH RECURSIVE x AS (SELECT 1) DELETE FROM t",
        "WITH x(a) AS (SELECT 1) DELETE FROM t",
        # finding 5: dollar-quoted DO block
        "DO $$ DELETE FROM t $$",
        # finding 6: extended file readers
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT read_csv_auto('/etc/passwd')",
        "SELECT read_ndjson('/tmp/x.ndjson')",
        "SELECT read_xlsx('/tmp/x.xlsx')",
        "SELECT read_text('/etc/passwd')",
        "SELECT sqlite_attach('/tmp/x.db')",
        "SELECT delta_scan('/tmp/delta')",
        # finding 7: doubled-quote escape near semicolon
        "SELECT 'a''; DROP TABLE t; --'",
        # finding 8: empty/whitespace/unterminated
        "",
        "   \n\t ",
        "/* unterminated comment",
        "SELECT 'unterminated",
        # N1: EXPLAIN ANALYZE executes the statement
        "EXPLAIN ANALYZE DELETE FROM t",
        "EXPLAIN (ANALYZE) DELETE FROM t",
        "EXPLAIN (ANALYZE, COSTS OFF) DELETE FROM t",
        "EXPLAIN INSERT INTO t VALUES (1)",
        # N3: SELECT INTO creates a table
        "SELECT * INTO newtab FROM data",
        # N4: catalog/stats writes and sequence mutation
        "COMMENT ON TABLE t IS 'x'",
        "VACUUM t",
        "ANALYZE t",
        "SELECT setval('seq', 42)",
        "SELECT nextval('seq')",
        # N5: pg_-prefixed file functions (non-string args so N2 can't mask them)
        "SELECT pg_read_server_files('/etc/passwd')",
        "SELECT pg_read_binary_file('/etc/passwd')",
        "SELECT pg_ls_dir('.')",
        "SELECT pg_ls_waldir()",
        "SELECT lo_import('/etc/passwd')",
        "SELECT lo_from_bytea(0, '\\x00')",
        # N6: session writes and locking clauses
        "SET search_path TO public",
        "RESET search_path",
        "SELECT * FROM t FOR UPDATE",
        "SELECT * FROM t FOR SHARE",
        "SELECT * FROM t FOR NO KEY UPDATE",
        # B1: British spelling of ANALYZE also executes in EXPLAIN
        "EXPLAIN ANALYSE DELETE FROM t",
        "EXPLAIN (ANALYSE) DELETE FROM t",
        "ANALYSE t",
        # B2: prepared statements smuggle writes across tool calls
        "PREPARE p AS DELETE FROM t",
        "EXECUTE p",
        # B3: disruptive / privilege-gated admin functions
        "SELECT pg_terminate_backend(123)",
        "SELECT pg_cancel_backend(123)",
        "SELECT pg_reload_conf()",
        "SELECT pg_advisory_lock(1)",
        "SELECT pg_stat_file('/etc/passwd')",
        # B4: table locks
        "LOCK TABLE t IN ACCESS EXCLUSIVE MODE",
    ],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        assert_read_only(sql)
