import factory

from udata.factories import ModelFactory

from .models import Organization, Team


class OrganizationFactory(ModelFactory):
    class Meta:
        model = Organization

    name = factory.Faker('sentence')
    description = factory.Faker('text')


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Faker('sentence')
