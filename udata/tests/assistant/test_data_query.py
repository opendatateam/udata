import pytest
from pydantic import TypeAdapter

from udata.core.assistant.data_query import (
    AndFilters,
    Filter,
    GenericFilter,
    OrFilters,
    build_data_query,
    filter_columns,
    filter_errors,
    with_page,
)


def test_grouped_aggregate_sorted_on_x():
    q = build_data_query(groupby="dep", aggregate=("n_cum_dose1", "max"), sort=("dep", "asc"))
    assert q == "dep__groupby&n_cum_dose1__max&dep__sort=asc"


def test_columns():
    assert build_data_query(columns=["a b", "c"]) == "columns=a%2520b,c"


def test_aggregate_without_groupby_is_a_global_total():
    assert build_data_query(aggregate=("n_cum_dose1", "sum")) == "n_cum_dose1__sum"


def test_with_page():
    assert with_page("a__groupby") == "a__groupby&page=1&page_size=50"
    assert with_page("") == "page=1&page_size=50"


def test_top_level_and_filters():
    f = AndFilters(
        filters=[
            Filter(column="dep", condition="differs", value="75"),
            Filter(column="reg", condition="is_null"),
        ]
    )
    assert build_data_query(filters=f) == "dep__differs=75&reg__isnull"


def test_or_group_with_nested_and():
    f = OrFilters(
        filters=[
            Filter(column="a", condition="exact", value="1"),
            AndFilters(
                filters=[
                    Filter(column="b", condition="greater", value="2.5"),
                    Filter(column="c", condition="is_not_null"),
                ]
            ),
        ]
    )
    assert build_data_query(filters=f) == (
        "or=(a__exact.%221%22,and(b__greater.%222%252E5%22,c__isnotnull))"
    )


def test_or_child_of_root_and():
    f = AndFilters(
        filters=[
            Filter(column="x", condition="exact", value="1"),
            OrFilters(
                filters=[
                    Filter(column="a", condition="exact", value="(1)"),
                    Filter(column="b", condition="less", value="2"),
                ]
            ),
        ]
    )
    assert build_data_query(filters=f) == (
        "x__exact=1&or=(a__exact.%22%25281%2529%22,b__less.%222%22)"
    )


def test_empty_values_are_dropped():
    assert build_data_query(filters=Filter(column="a", condition="exact", value="")) == ""
    assert build_data_query(filters=Filter(column="a", condition="exact")) == ""


def test_special_characters_are_encoded():
    f = Filter(column="Nom de l'élu", condition="exact", value="a&b")
    assert build_data_query(filters=f) == "Nom%2520de%2520l%27%25C3%25A9lu__exact=a%2526b"


@pytest.mark.parametrize(
    "value,encoded",
    [
        ("75", "75"),
        ("2.5", "2.5"),
        ("2021-01-01", "2021-01-01"),
        # api-tabular decodes the query string twice: a single-encoded # cuts
        # the request short and a literal %XX is decoded into another character.
        ("x#y", "x%2523y"),
        ("50%", "50%2525"),
        ("%C3%A9", "%2525C3%2525A9"),
        ("a+b", "a%252Bb"),
        (
            "Côte d'Azur (n°1), a;b.",
            "C%25C3%25B4te%2520d%27Azur%2520%28n%25C2%25B01%29%252C%2520a%253Bb.",
        ),
    ],
)
def test_simple_filter_values_are_double_encoded(value, encoded):
    assert build_data_query(filters=Filter(column="c", condition="exact", value=value)) == (
        f"c__exact={encoded}"
    )


@pytest.mark.parametrize(
    "value,encoded",
    [
        ("1", "1"),
        ("2.5", "2%252E5"),
        ("2021-01-01", "2021-01-01"),
        ("Île-de-France", "%C3%8Ele-de-France"),
        # or()/and() split on , ( ) and PostgREST's grammar on . — double-encoded
        ("a,b", "a%252Cb"),
        ("(1)", "%25281%2529"),
        # escaped inside the quoted value
        ('a"b', "a%5C%2522b"),
        ("a\\b", "a%5C%5Cb"),
        # decoded twice, like the simple filters
        ("x#y", "x%2523y"),
        ("50%", "50%2525"),
        ("&#8209;", "%26%25238209%3B"),
    ],
)
def test_group_values_are_quoted_and_escaped(value, encoded):
    group = OrFilters(filters=[Filter(column="c", condition="exact", value=value)])
    assert build_data_query(filters=group) == f"or=(c__exact.%22{encoded}%22)"


def test_filters_parse_from_the_cls_alias():
    f = TypeAdapter(GenericFilter).validate_python(
        {
            "_cls": "OrFilters",
            "filters": [{"_cls": "Filter", "column": "a", "condition": "exact", "value": "1"}],
        }
    )
    assert filter_columns(f) == {"a"}


def test_filter_columns_nested_and_none():
    assert filter_columns(None) == set()
    f = AndFilters(
        filters=[
            Filter(column="a", condition="exact", value="1"),
            OrFilters(filters=[Filter(column="b", condition="is_null")]),
        ]
    )
    assert filter_columns(f) == {"a", "b"}


def test_numeric_filter_value_is_coerced_to_a_string():
    f = TypeAdapter(GenericFilter).validate_python(
        {"_cls": "Filter", "column": "b", "condition": "greater", "value": 2.5}
    )
    assert f.value == "2.5"
    group = OrFilters(filters=[f])
    assert build_data_query(filters=group) == "or=(b__greater.%222%252E5%22)"


def test_filter_without_cls_parses_as_a_filter():
    f = TypeAdapter(GenericFilter).validate_python(
        {"column": "n", "condition": "greater", "value": 2}
    )
    assert isinstance(f, Filter)
    assert f.value == "2"
    assert build_data_query(filters=f) == "n__greater=2"
    assert f.model_dump(by_alias=True)["_cls"] == "Filter"


def test_group_children_without_cls_parse_as_filters():
    f = TypeAdapter(GenericFilter).validate_python(
        {"_cls": "AndFilters", "filters": [{"column": "a", "condition": "is_null"}]}
    )
    assert isinstance(f.filters[0], Filter)


def test_filter_errors_flags_every_condition_without_a_value():
    f = OrFilters(
        filters=[
            Filter(column="a", condition="exact"),
            AndFilters(
                filters=[
                    Filter(column="b", condition="greater", value=""),
                    Filter(column="c", condition="is_null"),
                    Filter(column="d", condition="less", value="0"),
                ]
            ),
        ]
    )
    assert filter_errors(f) == [
        "Le filtre exact sur a demande une valeur.",
        "Le filtre greater sur b demande une valeur.",
    ]


def test_filter_errors_accepts_null_conditions_and_no_filter():
    assert filter_errors(None) == []
    assert filter_errors(Filter(column="a", condition="is_not_null")) == []


def test_filter_errors_treats_a_blank_value_as_missing():
    assert filter_errors(Filter(column="a", condition="exact", value="  \t")) == [
        "Le filtre exact sur a demande une valeur."
    ]


# Verified against api-tabular main on PostgreSQL: decoded twice, like the values.
COLUMN_KEYS = {
    "Nb. habitants": "Nb.%2520habitants",
    "Taux (en points, 2020)": "Taux%2520%28en%2520points%252C%25202020%29",
    "Région": "R%25C3%25A9gion",
    "a&b": "a%2526b",
    "50%": "50%2525",
    "#1": "%25231",
}


@pytest.mark.parametrize("column,key", COLUMN_KEYS.items())
def test_column_names_of_top_level_parameters_are_double_encoded(column, key):
    assert (
        build_data_query(
            columns=[column, "x"],
            groupby=column,
            aggregate=(column, "max"),
            sort=(column, "asc"),
            filters=Filter(column=column, condition="exact", value="1"),
        )
        == f"columns={key},x&{key}__groupby&{key}__max&{key}__sort=asc&{key}__exact=1"
    )


# Unquoted: api-tabular reads a quoted column's operator as `[a-z]+`, which cuts strictly_*.
CONDITION_COLUMNS = {
    "Nb. habitants": "Nb%252E%20habitants",
    "Taux (en points, 2020)": "Taux%20%2528en%20points%252C%202020%2529",
    "Région": "R%C3%A9gion",
    "a&b": "a%26b",
    "50%": "50%2525",
    "#1": "%25231",
    "strictly": "strictly",
}


@pytest.mark.parametrize("column,encoded", CONDITION_COLUMNS.items())
def test_column_names_of_group_conditions_are_encoded_like_their_values(column, encoded):
    group = OrFilters(
        filters=[
            Filter(column=column, condition="strictly_greater", value="0"),
            Filter(column=column, condition="is_null"),
        ]
    )
    assert build_data_query(filters=group) == (
        f"or=({encoded}__strictly_greater.%220%22,{encoded}__isnull)"
    )
