import factory

from udata import utils
from udata.core.dataset.factories import DatasetFactory
from udata.factories import ModelFactory

from .models import Topic, TopicElement


class TopicElementFactory(ModelFactory):
    class Meta:
        model = TopicElement

    title = factory.Faker("sentence")
    description = factory.Faker("text")


class TopicElementDatasetFactory(TopicElementFactory):
    element = factory.SubFactory(DatasetFactory)


class TopicFactory(ModelFactory):
    class Meta:
        model = Topic

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    tags = factory.LazyAttribute(lambda o: [utils.unique_string(16) for _ in range(3)])
    private = False

    @factory.lazy_attribute
    def elements(self):
        # TODO: create more types
        return TopicElementDatasetFactory.create_batch(3)
