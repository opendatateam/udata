from uuid import uuid4

import pytest
from flask import url_for
from pydantic import ValidationError

from udata.core.assistant.charts import (
    CreateChartInput,
    UpdateChartInput,
    to_chart_output,
    to_update_output,
    unknown_column_errors,
    validate_create,
)
from udata.core.visualizations.models import Chart
from udata.tests.api import PytestOnlyAPITestCase

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


@pytest.mark.parametrize(
    "overrides",
    [
        {"x_axis": {"column_x": "zzz", "type": "discrete"}},
        {"series": [{"column_y": "zzz", "aggregate_y": "max"}]},
        {"filters": {"_cls": "Filter", "column": "zzz", "condition": "exact", "value": "1"}},
    ],
    ids=["x", "series", "filter"],
)
def test_unknown_column(overrides):
    assert validate_create(make(**overrides), COLUMNS) == ["Unknown column: zzz."]


def test_count_series_column_y_is_not_validated():
    # A count series counts the X column: its column_y is replaced, never read.
    config = make(series=[{"column_y": "zzz", "aggregate_y": "count"}])
    assert validate_create(config, COLUMNS) == []


def test_unknown_columns_are_reported_once_in_order():
    config = make(
        x_axis={"column_x": "a", "type": "discrete"},
        series=[{"column_y": "b", "aggregate_y": "max"}, {"column_y": "a", "aggregate_y": "max"}],
        filters={"_cls": "Filter", "column": "a", "condition": "exact", "value": "1"},
    )
    assert validate_create(config, COLUMNS) == [
        "Unknown column: a.",
        "Unknown column: b.",
    ]


@pytest.mark.parametrize("aggregate", ["sum", "avg", "min", "max"])
def test_numeric_aggregate_on_text_column_is_refused_on_a_chart_y_axis(aggregate):
    config = make(series=[{"column_y": "dep", "aggregate_y": aggregate}])
    assert validate_create(config, COLUMNS) == [
        f"The {aggregate} aggregate needs a numeric column: dep is of type string."
    ]


def test_count_on_text_column_is_allowed():
    config = make(series=[{"column_y": "dep", "aggregate_y": "count"}])
    assert validate_create(config, COLUMNS) == []


def test_no_aggregate_on_text_column_is_refused():
    config = make(series=[{"column_y": "dep"}])
    assert validate_create(config, COLUMNS) == [
        "The dep series must be numeric or aggregated by count."
    ]


def test_no_aggregate_on_numeric_column_is_allowed():
    config = make(series=[{"column_y": "n_cum_dose1"}])
    assert validate_create(config, COLUMNS) == []


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
    out = to_chart_output(config, "rid").model_dump()
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


def test_output_count_series_targets_the_x_column():
    # The chart form reads a series as a count when column_y is column_x.
    config = make(
        series=[
            {"column_y": "n_cum_dose1", "aggregate_y": "count"},
            {"column_y": "n_cum_dose1", "aggregate_y": "max"},
            {"column_y": "n_cum_dose1"},
        ]
    )
    out = to_chart_output(config, "rid").model_dump()
    assert [(s["column_y"], s["aggregate_y"]) for s in out["series"]] == [
        ("dep", "count"),
        ("n_cum_dose1", "max"),
        ("n_cum_dose1", None),
    ]


def test_output_keeps_one_count_series_in_order():
    # Every count series becomes the same count of the X column.
    config = make(
        series=[
            {"column_y": "n_cum_dose1", "aggregate_y": "max"},
            {"column_y": "n_cum_dose1", "aggregate_y": "count"},
            {"column_y": "n_cum_dose1"},
            {"column_y": "jour", "aggregate_y": "count"},
        ]
    )
    out = to_chart_output(config, "rid").model_dump()
    assert [(s["column_y"], s["aggregate_y"]) for s in out["series"]] == [
        ("n_cum_dose1", "max"),
        ("dep", "count"),
        ("n_cum_dose1", None),
    ]


def test_unknown_column_errors_are_deduplicated_in_order_and_skip_empty_names():
    assert unknown_column_errors(["b", None, "dep", "a", "b", ""], COLUMNS) == [
        "Unknown column: b.",
        "Unknown column: a.",
    ]


def test_output_without_filters_has_none():
    assert to_chart_output(make(), "rid").model_dump()["series"][0]["filters"] is None


def test_update_output_of_no_change_is_empty():
    assert to_update_output(UpdateChartInput()) == {}
    assert to_update_output(UpdateChartInput(y_axis={})) == {}


def test_update_output_only_has_provided_fields():
    patch = UpdateChartInput(y_axis={"unit": "doses"})
    assert to_update_output(patch) == {"y_axis": {"unit": "doses"}}


def test_unit_is_not_bounded_beyond_the_chart_model():
    # Like YAxis.unit and the chart form: a long unit is accepted.
    patch = UpdateChartInput(y_axis={"unit": "tonnes équivalent CO2"})
    assert to_update_output(patch) == {"y_axis": {"unit": "tonnes équivalent CO2"}}


def test_update_output_drops_top_level_nulls_but_keeps_y_axis_nulls():
    patch = UpdateChartInput(title="x", type=None, y_axis={"min": None, "unit": "u"})
    assert to_update_output(patch) == {"title": "x", "y_axis": {"min": None, "unit": "u"}}


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
    assert validate_create(config, COLUMNS) == ["The exact filter on dep needs a value."]


@pytest.mark.parametrize("field", ["title", "description"])
def test_blank_title_or_description_is_refused(field):
    with pytest.raises(ValidationError, match="at least 1 character"):
        make(**{field: "   "})


def test_output_strips_title_and_description():
    out = to_chart_output(
        make(title="  Doses ", description=" Par département "), "rid"
    ).model_dump()
    assert (out["title"], out["description"]) == ("Doses", "Par département")


@pytest.mark.parametrize("field", ["title", "description"])
def test_update_refuses_a_blank_title_or_description(field):
    with pytest.raises(ValidationError, match="at least 1 character"):
        UpdateChartInput(**{field: " "})


def test_the_tool_schema_asks_for_a_non_empty_title():
    schema = CreateChartInput.model_json_schema()
    assert schema["properties"]["title"]["minLength"] == 1


def test_update_output_strips_the_title():
    assert to_update_output(UpdateChartInput(title=" Neuf ")) == {"title": "Neuf"}


class ChartOutputMatchesTheChartModelTest(PytestOnlyAPITestCase):
    """The visualization API accepts what the assistant builds, as cdata saves it."""

    @pytest.mark.parametrize(
        "overrides",
        [
            {},
            {
                "type": "histogram",
                "x_axis": {
                    "column_x": "dep",
                    "type": "continuous",
                    "sort_x_by": "axis_y",
                    "sort_x_direction": "desc",
                    "limit": 50,
                },
                "series": [
                    {"column_y": "n_cum_dose1", "aggregate_y": "sum"},
                    {"column_y": "dep", "aggregate_y": "count"},
                ],
                "y_axis": {"label": "Doses", "unit": "%", "unit_position": "prefix", "min": 0},
            },
            {
                "filters": {
                    "_cls": "AndFilters",
                    "filters": [
                        {"column": "jour", "condition": "greater", "value": "2021-01-01"},
                        {
                            "_cls": "OrFilters",
                            "filters": [
                                {"column": "dep", "condition": "exact", "value": "75"},
                                {"column": "dep", "condition": "is_null"},
                            ],
                        },
                    ],
                },
            },
        ],
    )
    def test_the_chart_api_accepts_the_chart_output(self, overrides):
        self.login()
        chart = to_chart_output(make(**overrides), str(uuid4())).model_dump()

        response = self.post(url_for("api.visualizations"), chart)

        assert response.status_code == 201, response.json
        assert Chart.objects.count() == 1
