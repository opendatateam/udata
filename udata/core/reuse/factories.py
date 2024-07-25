import factory
from factory.fuzzy import FuzzyChoice

from udata.core.dataset.factories import DatasetFactory
from udata.factories import ModelFactory
from udata.utils import faker

from .constants import REUSE_TOPICS, REUSE_TYPES
from .models import Reuse


class ReuseFactory(ModelFactory):
    class Meta:
        model = Reuse

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    url = factory.LazyAttribute(lambda o: "/".join([faker.url(), faker.unique_string()]))
    type = FuzzyChoice(REUSE_TYPES.keys())
    topic = FuzzyChoice(REUSE_TOPICS.keys())
    archived = None

    class Params:
        visible = factory.Trait(datasets=factory.LazyAttribute(lambda o: [DatasetFactory()]))


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]
