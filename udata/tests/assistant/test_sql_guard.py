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
    ],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        assert_read_only(sql)
