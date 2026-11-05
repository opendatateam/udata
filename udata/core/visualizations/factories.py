import factory
from factory.fuzzy import FuzzyChoice

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
    query = "SELECT category, COUNT(*) AS total FROM data GROUP BY category"
    resource_id = factory.Faker("uuid4")
    chart_type = FuzzyChoice(["line", "histogram"])
