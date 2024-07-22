import factory

from udata.core.dataservices.models import Dataservice, HarvestMetadata
from udata.core.organization.factories import OrganizationFactory
from udata.factories import ModelFactory


class HarvestMetadataFactory(ModelFactory):
    class Meta:
        model = HarvestMetadata

    backend = "csw-dcat"
    domain = "data.gouv.fr"

    source_id = factory.Faker("unique_string")
    source_url = factory.Faker("url")

    remote_id = factory.Faker("unique_string")
    remote_url = factory.Faker("url")

    uri = factory.Faker("url")


class DataserviceFactory(ModelFactory):
    class Meta:
        model = Dataservice

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    base_api_url = factory.Faker("url")

    class Params:
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )
