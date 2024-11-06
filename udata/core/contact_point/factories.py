import factory

from udata.factories import ModelFactory

from .models import ContactPoint


class ContactPointFactory(ModelFactory):
    class Meta:
        model = ContactPoint

    name = factory.Faker("name")
    contact_form = factory.Faker("url")
    email = factory.Sequence(lambda n: "contact_point{}@example.com".format(n))
