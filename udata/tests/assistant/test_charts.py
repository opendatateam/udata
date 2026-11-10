import pytest
from pydantic import ValidationError

from udata.core.assistant.charts import (
    EMPTY_TEXT_ERRORS,
    CreateChartInput,
    UpdateChartInput,
    profile_columns,
    to_chart_output,
    to_update_output,
    validate_create,
    validate_update,
)

COLUMNS = {"dep": "string", "n_cum_dose1": "int", "jour": "date"}


def make(**overrides):
    data = {
        "title": "Doses",
        "description": "Doses par département",
        "type": "line",
        "x_axis": {"column_x": "dep", "type": "discrete"},
        "series": [{"column_y": "n_cum_dose1", "aggregate_y": "max"}],
    }
    data.update(overrides)
    return CreateChartInput(**data)


def test_valid_create_has_no_errors():
    assert validate_create(make(), COLUMNS) == []


def test_unknown_x_column():
    config = make(x_axis={"column_x": "region", "type": "discrete"})
    assert validate_create(config, COLUMNS) == ["Colonne inconnue : region."]


def test_unknown_series_column():
    config = make(series=[{"column_y": "zzz", "aggregate_y": "count"}])
    assert validate_create(config, COLUMNS) == ["Colonne inconnue : zzz."]


def test_unknown_filter_column():
    config = make(filters={"_cls": "Filter", "column": "foo", "condition": "exact", "value": "1"})
    assert validate_create(config, COLUMNS) == ["Colonne inconnue : foo."]


def test_errors_are_all_returned_deduplicated_in_order():
    config = make(
        x_axis={"column_x": "a", "type": "discrete"},
        series=[{"column_y": "b", "aggregate_y": "max"}, {"column_y": "a", "aggregate_y": "max"}],
        filters={"_cls": "Filter", "column": "a", "condition": "exact", "value": "1"},
    )
    assert validate_create(config, COLUMNS) == [
        "Colonne inconnue : a.",
        "Colonne inconnue : b.",
    ]


def test_sum_on_text_column_is_refused():
    config = make(series=[{"column_y": "dep", "aggregate_y": "sum"}])
    assert validate_create(config, COLUMNS) == [
        "L'agrégat sum demande une colonne numérique : dep est de type string."
    ]


@pytest.mark.parametrize("aggregate", ["min", "max"])
def test_min_max_on_text_column_is_refused_on_a_chart_y_axis(aggregate):
    config = make(series=[{"column_y": "dep", "aggregate_y": aggregate}])
    assert validate_create(config, COLUMNS) == [
        f"L'agrégat {aggregate} demande une colonne numérique : dep est de type string."
    ]


def test_count_on_text_column_is_allowed():
    config = make(series=[{"column_y": "dep", "aggregate_y": "count"}])
    assert validate_create(config, COLUMNS) == []


def test_no_aggregate_on_text_column_is_refused():
    config = make(series=[{"column_y": "dep"}])
    assert validate_create(config, COLUMNS) == [
        "La série dep doit être numérique ou agrégée par count."
    ]


def test_no_aggregate_on_numeric_column_is_allowed():
    config = make(series=[{"column_y": "n_cum_dose1"}])
    assert validate_create(config, COLUMNS) == []


def test_limit_bounds():
    for bad in (0, 51):
        with pytest.raises(ValidationError):
            make(x_axis={"column_x": "dep", "type": "discrete", "limit": bad})
    for good in (1, 50):
        make(x_axis={"column_x": "dep", "type": "discrete", "limit": good})


def test_output_applies_the_type_and_filters_to_every_series():
    filters = {"_cls": "Filter", "column": "dep", "condition": "exact", "value": "01"}
    config = make(
        type="histogram",
        filters=filters,
        series=[
            {"column_y": "n_cum_dose1", "aggregate_y": "max"},
            {"column_y": "dep", "aggregate_y": "count"},
        ],
    )
    out = to_chart_output(config, "rid")
    assert [s["type"] for s in out["series"]] == ["histogram", "histogram"]
    expected = {"_cls": "Filter", "column": "dep", "condition": "exact", "value": "01"}
    assert [s["filters"] for s in out["series"]] == [expected, expected]
    assert all(s["column_x_name_override"] is None for s in out["series"])
    assert out["x_axis"]["limit"] is None
    assert out["y_axis"] == {
        "label": None,
        "unit": None,
        "unit_position": None,
        "min": None,
        "max": None,
    }


def test_output_without_filters_has_none():
    assert to_chart_output(make(), "rid")["series"][0]["filters"] is None


def test_output_injects_the_resource_id():
    out = to_chart_output(make(), "abc")
    assert out["series"][0]["resource_id"] == "abc"
    assert out["title"] == "Doses"


def test_update_needs_one_field():
    assert validate_update(UpdateChartInput()) == ["Au moins une modification est requise."]
    assert validate_update(UpdateChartInput(y_axis={})) == [
        "Au moins une modification est requise."
    ]
    assert validate_update(UpdateChartInput(title="x")) == []


def test_update_output_only_has_provided_fields():
    patch = UpdateChartInput(y_axis={"unit": "doses"})
    assert to_update_output(patch) == {"y_axis": {"unit": "doses"}}


def test_profile_columns_follows_the_header_order():
    profile = {
        "profile": {
            "header": ["b", "a"],
            "columns": {"a": {"python_type": "int"}, "b": {"python_type": "string"}},
        }
    }
    cols = profile_columns(profile)
    assert list(cols) == ["b", "a"]
    assert cols == {"b": "string", "a": "int"}


def test_profile_columns_malformed_returns_empty():
    assert profile_columns({}) == {}
    assert profile_columns({"profile": "x"}) == {}
    assert profile_columns({"profile": {"header": 3, "columns": []}}) == {}


def test_update_with_only_nulls_is_an_error():
    patch = UpdateChartInput(title=None, y_axis=None)
    assert validate_update(patch) == ["Au moins une modification est requise."]
    assert to_update_output(patch) == {}


def test_update_output_drops_top_level_nulls_but_keeps_y_axis_nulls():
    patch = UpdateChartInput(title="x", type=None, y_axis={"min": None, "unit": "u"})
    assert to_update_output(patch) == {"title": "x", "y_axis": {"min": None, "unit": "u"}}


def test_output_series_do_not_share_filters():
    filters = {"_cls": "Filter", "column": "dep", "condition": "exact", "value": "01"}
    config = make(
        filters=filters,
        series=[{"column_y": "n_cum_dose1"}, {"column_y": "n_cum_dose1", "aggregate_y": "max"}],
    )
    out = to_chart_output(config, "rid")
    out["series"][0]["filters"]["value"] = "changed"
    assert out["series"][1]["filters"]["value"] == "01"


@pytest.mark.parametrize(
    "field,value",
    [
        ("x_axis", {"column_x": "dep", "type": "discrete"}),
        ("series", [{"column_y": "n_cum_dose1"}]),
        ("filters", {"column": "dep", "condition": "exact", "value": "1"}),
    ],
)
def test_update_refuses_structural_fields(field, value):
    with pytest.raises(ValidationError):
        UpdateChartInput(**{field: value})


def test_filter_without_value_is_refused():
    config = make(filters={"column": "dep", "condition": "exact", "value": None})
    assert validate_create(config, COLUMNS) == ["Le filtre exact sur dep demande une valeur."]


@pytest.mark.parametrize("field", ["title", "description"])
def test_blank_title_or_description_is_refused(field):
    errors = validate_create(make(**{field: "   "}), COLUMNS)
    assert errors == [EMPTY_TEXT_ERRORS[field]]


def test_description_is_required():
    with pytest.raises(ValidationError):
        CreateChartInput(
            title="Doses",
            type="line",
            x_axis={"column_x": "dep", "type": "discrete"},
            series=[{"column_y": "n_cum_dose1"}],
        )


def test_output_strips_title_and_description():
    out = to_chart_output(make(title="  Doses ", description=" Par département "), "rid")
    assert (out["title"], out["description"]) == ("Doses", "Par département")


@pytest.mark.parametrize("field", ["title", "description"])
def test_update_refuses_a_blank_title_or_description(field):
    assert validate_update(UpdateChartInput(**{field: " "})) == [EMPTY_TEXT_ERRORS[field]]


def test_update_output_strips_the_title():
    assert to_update_output(UpdateChartInput(title=" Neuf ")) == {"title": "Neuf"}
