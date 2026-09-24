import pytest

from udata.tests.helpers import argvalues


class ArgvaluesTest:
    def test_last_tuple_value_becomes_the_id(self):
        params = argvalues((1, 2, "x"), (3, 4, "y"))

        assert [(p.values, p.id) for p in params] == [((1, 2), "x"), ((3, 4), "y")]

    def test_single_argument_parameter_sets(self):
        params = argvalues((None, "none"), ("http://example.com/", "trailing-slash"))

        assert [(p.values, p.id) for p in params] == [
            ((None,), "none"),
            (("http://example.com/",), "trailing-slash"),
        ]

    def test_single_iterable_of_parameter_sets(self):
        params = argvalues((n * 2, str(n)) for n in (1, 2))

        assert [(p.values, p.id) for p in params] == [((2,), "1"), ((4,), "2")]

    def test_ids_callable_receives_the_whole_values_tuple(self):
        params = argvalues((1, 2), (3, 4), ids=lambda values: f"sum-{sum(values)}")

        assert [(p.values, p.id) for p in params] == [((1, 2), "sum-3"), ((3, 4), "sum-7")]

    @pytest.mark.parametrize("value", argvalues((1, "one"), (2, "two")))
    def test_ids_are_used_by_pytest_as_parameter_set_ids(self, request, value):
        assert request.node.callspec.id == {1: "one", 2: "two"}[value]
