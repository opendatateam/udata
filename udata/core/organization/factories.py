import factory

from udata.factories import ModelFactory

from .models import Organization, Team, Member


class OrganizationFactory(ModelFactory):
    class Meta:
        model = Organization

    name = factory.Faker('sentence')
    description = factory.Faker('text')
    members = factory.LazyAttribute(lambda o: [
        Member(user=user, role='admin')
        for user in o.admins
    ] + [
        Member(user=user, role='editor')
        for user in o.editors
    ])

    class Params:
        admins = []
        editors = []


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Faker('sentence')
