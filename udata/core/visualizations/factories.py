import factory
import factory.fuzzy

from udata.factories import ModelFactory

from .models import Chart, DataSeries, Filter, XAxis, YAxis


class XAxisFactory(ModelFactory):
    class Meta:
        model = XAxis

    column_x = factory.Faker("word")
    type = "discrete"


class YAxisFactory(ModelFactory):
    class Meta:
        model = YAxis

    label = factory.Faker("word")


class DataSeriesFactory(ModelFactory):
    class Meta:
        model = DataSeries

    type = "line"
    column_y = factory.Faker("word")
    resource_id = factory.Faker("uuid4")


class FilterFactory(ModelFactory):
    class Meta:
        model = Filter

    column = factory.Faker("word")
    condition = factory.fuzzy.FuzzyChoice(
        [
            "exact",
            "differs",
            "is_null",
            "is_not_null",
            "greater",
            "less",
            "strictly_greater",
            "strictly_less",
        ]
    )
    value = factory.Faker("word")


class ChartFactory(ModelFactory):
    class Meta:
        model = Chart

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    x_axis = factory.SubFactory(XAxisFactory)
    y_axis = factory.SubFactory(YAxisFactory)
    series = factory.List([factory.SubFactory(DataSeriesFactory)])
