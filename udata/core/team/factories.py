import factory

from udata.factories import ModelFactory

from .models import Team


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Faker('sentence')
    description = factory.Faker('text')
