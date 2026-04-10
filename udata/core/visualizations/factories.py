import factory

from udata.factories import ModelFactory

from .models import Chart, DataSeries, XAxis, YAxis


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


class ChartFactory(ModelFactory):
    class Meta:
        model = Chart

    title = factory.Faker("sentence")
    description = factory.Faker("text")
