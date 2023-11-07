import factory

from udata import utils
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.factories import ModelFactory

from .models import Topic


class TopicFactory(ModelFactory):
    class Meta:
        model = Topic

    name = factory.Faker('sentence')
    description = factory.Faker('text')
    tags = factory.LazyAttribute(lambda o: [utils.unique_string(16)
                                 for _ in range(3)])

    @factory.lazy_attribute
    def datasets(self):
        return VisibleDatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return VisibleReuseFactory.create_batch(3)
