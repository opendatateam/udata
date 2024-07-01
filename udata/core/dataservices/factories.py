import factory

from udata.core.dataservices.models import Dataservice
from udata.core.organization.factories import OrganizationFactory
from udata.factories import ModelFactory


class DataserviceFactory(ModelFactory):
    class Meta:
        model = Dataservice

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    base_api_url = factory.Faker('url')

    class Params:
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )