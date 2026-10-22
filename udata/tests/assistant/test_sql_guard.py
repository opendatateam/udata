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
    ],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        assert_read_only(sql)
