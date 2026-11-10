import factory
import factory.fuzzy

from udata.factories import ModelFactory

from .models import CONTACT_ROLES, ContactPoint


class ContactPointFactory(ModelFactory):
    class Meta:
        model = ContactPoint

    name = factory.Faker("name")
    contact_form = factory.Faker("url")
    email = factory.Sequence(lambda n: f"contact_point{n}@example.com")
    role = factory.fuzzy.FuzzyChoice(CONTACT_ROLES.keys())
