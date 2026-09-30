import itertools

import factory

from udata.core.organization.factories import OrganizationFactory
from udata.factories import ModelFactory

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


class DataserviceFactory(ModelFactory):
    class Meta:
        model = Dataservice

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    base_api_url = factory.Faker("url")

    # FIXME: reset like factory does
    _ids = itertools.count()

    @factory.post_generation
    def remote_id(obj, create, extracted, **kwargs):
        """Sets dataset.remote_id. In-memory only, not saved in the mongo document.

        If remote_id is:
        - falsy => attribute not set
        - True => attribute set to "dataset-0", "dataset-1", ...
        - string => attribute set to string value (will collide if more than one instance share the same id)
        - callable(i) => attribute set to returned value (with i a sequence number)
        """
        if extracted is True:
            extracted = lambda i: f"{type(obj).__name__.lower()}-{i}"  # noqa: E731
        if callable(extracted):
            extracted = extracted(next(DataserviceFactory._ids))
        if extracted:
            obj.remote_id = extracted

    @factory.post_generation
    def timestamps(obj, create, extracted, **kwargs):
        if extracted is False:
            for field in ("created_at_internal", "last_modified_internal", "last_update"):
                obj._data[field] = None

    class Params:
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )
