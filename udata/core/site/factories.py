import factory

from udata.factories import ModelFactory

from .models import Site, SiteSettings


class SiteSettingsFactory(ModelFactory):
    class Meta:
        model = SiteSettings


class SiteFactory(ModelFactory):
    class Meta:
        model = Site

    id = factory.Faker('word')
    title = factory.Faker('name')
    settings = factory.SubFactory(SiteSettingsFactory)
