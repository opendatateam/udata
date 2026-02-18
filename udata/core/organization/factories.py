import factory

from udata.factories import ModelFactory

from .models import Member, Organization, Team


class OrganizationFactory(ModelFactory):
    class Meta:
        model = Organization

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    members = factory.LazyAttribute(
        lambda o: [Member(user=user, role="admin") for user in o.admins]
        + [Member(user=user, role="editor") for user in o.editors]
        + [Member(user=user, role="partial_editor") for user in o.partial_editors]
    )

    class Params:
        admins = []
        editors = []
        partial_editors = []


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Faker("sentence")
