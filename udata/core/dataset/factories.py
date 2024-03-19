import factory

import json
from os.path import join

from udata.app import ROOT_DIR
from udata.factories import ModelFactory

from .models import Dataset, Resource, Checksum, CommunityResource, License

from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory


class DatasetFactory(ModelFactory):
    class Meta:
        model = Dataset

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    frequency = 'unknown'
    resources = factory.LazyAttribute(lambda o: ResourceFactory.build_batch(o.nb_resources))

    class Params:
        geo = factory.Trait(
            spatial=factory.SubFactory(SpatialCoverageFactory)
        )
        visible = factory.Trait(
            resources=factory.LazyAttribute(lambda o: [ResourceFactory()])
        )
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )
        nb_resources = 0


class VisibleDatasetFactory(DatasetFactory):
    @factory.lazy_attribute
    def resources(self):
        return [ResourceFactory()]


class ChecksumFactory(ModelFactory):
    class Meta:
        model = Checksum

    type = 'sha1'
    value = factory.Faker('sha1')


class BaseResourceFactory(ModelFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('text')
    filetype = 'file'
    type = 'documentation'
    url = factory.Faker('url')
    checksum = factory.SubFactory(ChecksumFactory)
    mime = factory.Faker('mime_type', category='text')
    filesize = factory.Faker('pyint')


class CommunityResourceFactory(BaseResourceFactory):
    class Meta:
        model = CommunityResource


class ResourceFactory(BaseResourceFactory):
    class Meta:
        model = Resource


class LicenseFactory(ModelFactory):
    class Meta:
        model = License

    id = factory.Faker('unique_string')
    title = factory.Faker('sentence')
    url = factory.Faker('uri')

class ResourceSchemaMockData():
    @staticmethod
    def get_mock_data():
        return json.load(open(join(ROOT_DIR, 'tests', 'schemas.json')))
    
    @staticmethod
    def get_expected_v1_result_from_mock_data():
        return [
            {
                "id": "etalab/schema-irve-statique",
                "label": "IRVE statique",
                "versions": [
                    "2.2.0",
                    "2.2.1"
                ]
            },
            {
                "id": "139bercy/format-commande-publique",
                "label": "Données essentielles des marchés publics français",
                "versions": [
                    "1.3.0",
                    "1.4.0",
                    "1.5.0",
                    "2.0.0",
                    "2.0.1"
                ]
            }
        ]