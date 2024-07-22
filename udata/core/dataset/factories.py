import json
from os.path import join

import factory

from udata.app import ROOT_DIR
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.factories import ModelFactory

from .models import Checksum, CommunityResource, Dataset, License, Resource


class DatasetFactory(ModelFactory):
    class Meta:
        model = Dataset

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    frequency = "unknown"
    resources = factory.LazyAttribute(lambda o: ResourceFactory.build_batch(o.nb_resources))

    class Params:
        geo = factory.Trait(spatial=factory.SubFactory(SpatialCoverageFactory))
        visible = factory.Trait(resources=factory.LazyAttribute(lambda o: [ResourceFactory()]))
        org = factory.Trait(
            organization=factory.SubFactory(OrganizationFactory),
        )
        nb_resources = 0


class HiddenDatasetFactory(DatasetFactory):
    private = True


class ChecksumFactory(ModelFactory):
    class Meta:
        model = Checksum

    type = "sha1"
    value = factory.Faker("sha1")


class BaseResourceFactory(ModelFactory):
    title = factory.Faker("sentence")
    description = factory.Faker("text")
    filetype = "file"
    type = "documentation"
    url = factory.Faker("url")
    checksum = factory.SubFactory(ChecksumFactory)
    mime = factory.Faker("mime_type", category="text")
    filesize = factory.Faker("pyint")


class CommunityResourceFactory(BaseResourceFactory):
    class Meta:
        model = CommunityResource


class ResourceFactory(BaseResourceFactory):
    class Meta:
        model = Resource


class LicenseFactory(ModelFactory):
    class Meta:
        model = License

    id = factory.Faker("unique_string")
    title = factory.Faker("sentence")
    url = factory.Faker("uri")


class ResourceSchemaMockData:
    @staticmethod
    def get_mock_data():
        return json.load(open(join(ROOT_DIR, "tests", "schemas.json")))

    @staticmethod
    def get_all_schemas_from_mock_data(with_datapackage_info=True):
        """
        with_datapackage_info is here to allow testing with or without marshalling (marshalling add None for inexistant datapackage_* fields)
        """
        schemas = ResourceSchemaMockData.get_expected_assignable_schemas_from_mock_data(
            with_datapackage_info
        )

        datapackage = {
            "name": "etalab/schema-irve",
            "title": "Infrastructures de recharges pour v\u00e9hicules \u00e9lectriques (IRVE)",
            "description": "data package contenant 2 sch\u00e9mas : IRVE statique et IRVE dynamique",
            "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve/latest/datapackage.json",
            "schema_type": "datapackage",
            "contact": "contact@transport.beta.gouv.fr",
            "examples": [],
            "labels": ["Socle Commun des Donn\u00e9es Locales", "transport.data.gouv.fr"],
            "consolidation_dataset_id": "5448d3e0c751df01f85d0572",
            "versions": [
                {
                    "version_name": "2.2.0",
                    "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve/2.2.0/datapackage.json",
                },
                {
                    "version_name": "2.2.1",
                    "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve/2.2.1/datapackage.json",
                },
                {
                    "version_name": "2.3.0",
                    "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve/2.3.0/datapackage.json",
                },
                {
                    "version_name": "2.3.1",
                    "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve/2.3.1/datapackage.json",
                },
            ],
            "external_doc": "https://doc.transport.data.gouv.fr/producteurs/infrastructures-de-recharge-de-vehicules-electriques-irve",
            "external_tool": None,
            "homepage": "https://github.com/etalab/schema-irve.git",
        }

        if with_datapackage_info:
            datapackage["datapackage_title"] = None
            datapackage["datapackage_name"] = None
            datapackage["datapackage_description"] = None

        return [datapackage] + schemas

    @staticmethod
    def get_expected_assignable_schemas_from_mock_data(with_datapackage_info=True):
        """
        with_datapackage_info is here to allow testing with or without marshalling (marshalling add None for inexistant datapackage_* fields)
        """
        schemas = [
            {
                "name": "etalab/schema-irve-statique",
                "title": "IRVE statique",
                "description": "Sp\u00e9cification du fichier d'\u00e9change relatif aux donn\u00e9es concernant la localisation g\u00e9ographique et les caract\u00e9ristiques techniques des stations et des points de recharge pour v\u00e9hicules \u00e9lectriques",
                "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/latest/schema-statique.json",
                "schema_type": "tableschema",
                "contact": "contact@transport.beta.gouv.fr",
                "examples": [
                    {
                        "title": "Exemple de fichier IRVE valide",
                        "path": "https://github.com/etalab/schema-irve/raw/v2.2.1/exemple-valide.csv",
                    }
                ],
                "labels": ["Socle Commun des Donn\u00e9es Locales", "transport.data.gouv.fr"],
                "consolidation_dataset_id": "5448d3e0c751df01f85d0572",
                "versions": [
                    {
                        "version_name": "2.2.0",
                        "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/2.2.0/schema-statique.json",
                    },
                    {
                        "version_name": "2.2.1",
                        "schema_url": "https://schema.data.gouv.fr/schemas/etalab/schema-irve-statique/2.2.1/schema-statique.json",
                    },
                ],
                "external_doc": "https://doc.transport.data.gouv.fr/producteurs/infrastructures-de-recharge-de-vehicules-electriques-irve",
                "external_tool": None,
                "homepage": "https://github.com/etalab/schema-irve.git",
                "datapackage_title": "Infrastructures de recharges pour v\u00e9hicules \u00e9lectriques (IRVE)",
                "datapackage_name": "etalab/schema-irve",
                "datapackage_description": "data package contenant 2 sch\u00e9mas : IRVE statique et IRVE dynamique",
            },
            {
                "name": "139bercy/format-commande-publique",
                "title": "Donn\u00e9es essentielles des march\u00e9s publics fran\u00e7ais",
                "description": "Donn\u00e9es des attributions de march\u00e9s publics et de contrats de concessions sup\u00e9rieures \u00e0 40 000 euros.",
                "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/latest/marches.json",
                "schema_type": "jsonschema",
                "contact": "schema@data.gouv.fr",
                "examples": [],
                "labels": [],
                "consolidation_dataset_id": None,
                "versions": [
                    {
                        "version_name": "1.3.0",
                        "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/1.3.0/sch\u00e9mas/json/contrats-concessions.json",
                    },
                    {
                        "version_name": "1.4.0",
                        "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/1.4.0/marches.json",
                    },
                    {
                        "version_name": "1.5.0",
                        "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/1.5.0/marches.json",
                    },
                    {
                        "version_name": "2.0.0",
                        "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/2.0.0/marches.json",
                    },
                    {
                        "version_name": "2.0.1",
                        "schema_url": "https://schema.data.gouv.fr/schemas/139bercy/format-commande-publique/2.0.1/marches.json",
                    },
                ],
                "external_doc": None,
                "external_tool": None,
                "homepage": "https://github.com/139bercy/format-commande-publique",
            },
        ]

        if with_datapackage_info:
            schemas[1]["datapackage_title"] = None
            schemas[1]["datapackage_name"] = None
            schemas[1]["datapackage_description"] = None

        return schemas
