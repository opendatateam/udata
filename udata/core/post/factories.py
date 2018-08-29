import factory

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.factories import ModelFactory

from .models import Post


class PostFactory(ModelFactory):
    class Meta:
        model = Post

    name = factory.Faker('sentence')
    headline = factory.Faker('sentence')
    content = factory.Faker('text')
    published = factory.Faker('past_datetime')

    @factory.lazy_attribute
    def datasets(self):
        return DatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return ReuseFactory.create_batch(3)
