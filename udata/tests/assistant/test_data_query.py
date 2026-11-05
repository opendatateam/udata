from pydantic import TypeAdapter

from udata.core.assistant.data_query import (
    AndFilters,
    Filter,
    GenericFilter,
    OrFilters,
    build_data_query,
    filter_columns,
    with_page,
)


def test_grouped_aggregate_sorted_on_x():
    q = build_data_query(groupby="dep", aggregate=("n_cum_dose1", "max"), sort=("dep", "asc"))
    assert q == "dep__groupby&n_cum_dose1__max&dep__sort=asc"


def test_columns():
    assert build_data_query(columns=["a b", "c"]) == "columns=a%20b,c"


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
    assert build_data_query(filters=f) == "or=(a__exact.1,and(b__greater.2%252E5,c__isnotnull))"


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
    assert build_data_query(filters=f) == "x__exact=1&or=(a__exact.%25281%2529,b__less.2)"


def test_empty_values_are_dropped():
    assert build_data_query(filters=Filter(column="a", condition="exact", value="")) == ""
    assert build_data_query(filters=Filter(column="a", condition="exact")) == ""


def test_special_characters_are_encoded():
    f = Filter(column="Nom de l'élu", condition="exact", value="a&b")
    # encodeURIComponent leaves the apostrophe untouched
    assert build_data_query(filters=f) == "Nom%20de%20l'%C3%A9lu__exact=a%26b"


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
