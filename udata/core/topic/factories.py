import factory

from udata import utils
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.factories import ModelFactory

from .models import Topic


class TopicFactory(ModelFactory):
    class Meta:
        model = Topic

    name = factory.Faker('sentence')
    description = factory.Faker('text')
    tags = factory.LazyAttribute(lambda o: [utils.unique_string(16)
                                 for _ in range(3)])
    datasets = []
    reuses = []
