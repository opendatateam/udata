import factory

from udata.factories import ModelFactory

from .models import Issue


class IssueFactory(ModelFactory):
    class Meta:
        model = Issue

    title = factory.Faker('sentence')
