import factory

from udata.core.organization.factories import OrganizationFactory
from udata.factories import HarvestableFactoryMixin, ModelFactory

from .models import Dataservice, HarvestDataserviceMetadata


class HarvestMetadataFactory(ModelFactory):
    class Meta:
        model = HarvestDataserviceMetadata

    backend = "csw-dcat"
    domain = "data.gouv.fr"

    source_id = factory.Faker("unique_string")
    source_url = factory.Faker("url")

    remote_id = factory.Faker("unique_string")
    remote_url = factory.Faker("url")

    uri = factory.Faker("url")

    created_at = factory.Faker("date_time")
    issued_at = factory.Faker("date_time")


class DataserviceFactory(HarvestableFactoryMixin, ModelFactory):
    class Meta:
        model = Dataservice

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    base_api_url = factory.Faker("url")

    class Params:
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )
