import factory

from udata.factories import ModelFactory

from .models import Chart, YAxis


class YAxisFactory(ModelFactory):
    class Meta:
        model = YAxis

    label = factory.Faker("word")


class ChartFactory(ModelFactory):
    class Meta:
        model = Chart

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    y_axis = factory.SubFactory(YAxisFactory)
    query = factory.Faker("sentence")
    resource_id = factory.Faker("uuid4")
