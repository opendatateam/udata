import copy
import datetime

from udata_search_service.consumers import (
    DataserviceConsumer,
    DatasetConsumer,
    OrganizationConsumer,
    ReuseConsumer,
)
from udata_search_service.utils import get_concat_title_org, log2p, mdstrip


def test_parse_dataset_obj():
    obj = {
        "id": "5c4ae55a634f4117716d5656",
        "title": "Demandes de valeurs foncières",
        "description": "### Propos liminaires...",
        "acronym": "DVF",
        "url": "/fr/datasets/demandes-de-valeurs-foncieres/",
        "tags": ["foncier", "foncier-sol-mutation-fonciere", "fonciere", "valeur-fonciere"],
        "license": "notspecified",
        "badges": [],
        "frequency": "semiannual",
        "created_at": "2019-01-25T11:30:50",
        "last_update": "2020-02-27T12:32:50",
        "views": 7806,
        "followers": 72,
        "reuses": 45,
        "featured": 0,
        "resources_count": 10,
        "resources": [
            {"id": "5ffa8553-0e8f-4622-add9-5c0b593ca1f8", "title": "Valeurs foncières 2024"},
            {"id": "bc213c7c-c4d4-4385-bf1f-719573d39e90", "title": "Valeurs foncières 2023"},
        ],
        "organization": {
            "id": "534fff8ea3a7292c64a77f02",
            "name": "Ministère de l'économie, des finances et de la relance",
            "public_service": 1,
            "followers": 401,
            "badges": ["public-service"],
        },
        "owner": None,
        "format": ["pdf", "pdf", "pdf", "pdf", "txt", "txt", "txt", "txt", "txt", "txt"],
        "temporal_coverage_start": "2016-07-01T00:00:00",
        "temporal_coverage_end": "2021-06-30T00:00:00",
        "geozones": [
            {"id": "fr:arrondissement:353", "name": "Rennes", "keys": ["353"]},
            {"id": "country-group:world"},
            {"id": "country:fr"},
            {"id": "country-group:ue"},
        ],
        "granularity": "fr:commune",
        "schema_": ["etalab/schema-irve"],
    }
    document = DatasetConsumer.load_from_dict(copy.deepcopy(obj)).to_dict()

    for key in [
        "id",
        "title",
        "url",
        "frequency",
        "resources_count",
        "acronym",
        "badges",
        "tags",
        "license",
        "owner",
    ]:
        assert document[key] == obj[key]

    assert document["description"] == mdstrip(obj["description"])
    assert document["schema"] == obj["schema_"]

    for key in ["views", "followers", "reuses"]:
        assert document[key] == log2p(obj[key])

    assert document["concat_title_org"] == get_concat_title_org(
        document["title"], document["acronym"], document["organization_name"]
    )
    assert document["created_at"].date() == datetime.date(2019, 1, 25)
    assert document["last_update"].date() == datetime.date(2020, 2, 27)
    assert document["temporal_coverage_start"].date() == datetime.date(2016, 7, 1)
    assert document["temporal_coverage_end"].date() == datetime.date(2021, 6, 30)
    assert document["granularity"] == "fr:commune"
    assert document["geozones"] == [
        "fr:arrondissement:353",
        "country-group:world",
        "country:fr",
        "country-group:ue",
    ]
    assert document["organization"] == obj["organization"]["id"]
    assert document["organization_name"] == obj["organization"]["name"]
    assert document["organization_badges"] == obj["organization"]["badges"]
    assert document["orga_followers"] == log2p(401)
    assert document["resources_ids"] == [res["id"] for res in obj["resources"]]
    assert document["resources_titles"] == [res["title"] for res in obj["resources"]]
    assert document["orga_sp"] == 4
    assert document["featured"] == 1


def test_parse_reuse_obj():
    obj = {
        "id": "5cc2dfbe8b4c414c91ffc46d",
        "title": "Explorateur de données de valeur foncière (DVF)",
        "description": "Cartographie des mutations à titre onéreux (parcelles en bleu).",
        "url": "https://app.dvf.etalab.gouv.fr/",
        "created_at": "2019-04-26T12:38:54",
        "views": 4326,
        "followers": 11,
        "datasets": 2,
        "featured": 1,
        "organization": {
            "id": "534fff75a3a7292c64a77de4",
            "name": "Etalab",
            "public_service": 1,
            "followers": 357,
            "badges": ["public-service"],
        },
        "owner": None,
        "type": "application",
        "topic": "housing_and_development",
        "tags": [
            "application-cartographique",
            "cadastre",
            "dgfip",
            "dvf",
            "etalab",
            "foncier",
            "mutations",
        ],
        "badges": [],
    }
    document = ReuseConsumer.load_from_dict(copy.deepcopy(obj)).to_dict()

    for key in ["id", "title", "url", "datasets", "featured", "badges", "tags", "owner"]:
        assert document[key] == obj[key]

    assert document["description"] == mdstrip(obj["description"])

    for key in ["views", "followers"]:
        assert document[key] == log2p(obj[key])

    assert document["created_at"].date() == datetime.date(2019, 4, 26)
    assert document["organization"] == obj["organization"]["id"]
    assert document["organization_name"] == obj["organization"]["name"]
    assert document["organization_badges"] == obj["organization"]["badges"]
    assert document["orga_followers"] == log2p(obj["organization"]["followers"])


def test_parse_dataservice_obj():
    obj = {
        "id": "670786ec0e65e6a0c784bf24",
        "title": "API INES",
        "description": "### À quoi sert l'API INES ?\n\nL'API INES permet la vérification.",
        "created_at": "2024-10-10T07:49:00",
        "views": 4326,
        "followers": 0,
        "organization": {
            "id": "534fff90a3a7292c64a77f45",
            "name": "Ministère de l'Enseignement supérieur et de la Recherche",
            "public_service": 1,
            "followers": 152,
        },
        "owner": None,
        "tags": [
            "education",
            "enseignement",
            "identifiant",
            "immatriculation",
            "ines",
            "verification",
        ],
        "is_restricted": False,
        "extras": {
            "availability_url": "",
            "is_franceconnect": False,
            "public_cible": [],
        },
    }
    document = DataserviceConsumer.load_from_dict(copy.deepcopy(obj)).to_dict()

    for key in ["id", "title", "tags", "owner", "is_restricted"]:
        assert document[key] == obj[key]

    assert document["description"] == mdstrip(obj["description"])

    for key in ["views", "followers"]:
        assert document[key] == log2p(obj[key])

    assert document["created_at"].date() == datetime.date(2024, 10, 10)
    assert document["organization"] == obj["organization"]["id"]
    assert document["organization_name"] == obj["organization"]["name"]
    assert document["orga_followers"] == log2p(obj["organization"]["followers"])
    assert document["description_length"] == log2p(len(mdstrip(obj["description"])))


def test_parse_organization_obj():
    obj = {
        "id": "534fff75a3a7292c64a77de4",
        "name": "Etalab",
        "acronym": None,
        "description": "Etalab est un département de la direction interministérielle du numérique (DINUM)",
        "url": "https://www.etalab.gouv.fr",
        "badges": ["public-service", "certified"],
        "created_at": "2014-04-17T18:21:09",
        "orga_sp": 1,
        "followers": 357,
        "datasets": 56,
        "views": 42,
        "reuses": 0,
    }
    document = OrganizationConsumer.load_from_dict(copy.deepcopy(obj)).to_dict()

    for key in ["id", "name", "acronym", "url", "badges", "datasets", "reuses"]:
        assert document[key] == obj[key]

    assert document["description"] == mdstrip(obj["description"])

    assert document["followers"] == log2p(obj["followers"])
    assert document["views"] == log2p(obj["views"])

    assert document["created_at"].date() == datetime.date(2014, 4, 17)
    assert document["orga_sp"] == 4
