from udata.core.spatial.commands import load_zones
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import GeoZone
from udata.search.fields import GeoZoneAncestorsFilter
from udata.tests.api import APITestCase
from udata_search_service.services import DatasetService


class GeoZoneAncestorsTest(APITestCase):
    def test_load_zones_persists_ancestors(self):
        load_zones(
            GeoZone,
            [
                {
                    "_id": "fr:departement:29",
                    "nom": "Finistère",
                    "level": "fr:departement",
                    "codeINSEE": "29",
                    "uri": "http://id.insee.fr/geo/departement/29",
                    "ancestors": ["country:fr", "fr:region:53"],
                }
            ],
        )
        assert GeoZone.objects.get(id="fr:departement:29").ancestors == [
            "country:fr",
            "fr:region:53",
        ]

    def test_filter_expands_zone_with_ancestors(self):
        GeoZoneFactory(id="fr:departement:29", ancestors=["country:fr", "fr:region:53"])
        value = GeoZoneAncestorsFilter.validate_parameter("fr:departement:29")
        assert value == ["fr:departement:29", "country:fr", "fr:region:53"]

    def test_filter_keeps_unknown_zone(self):
        assert GeoZoneAncestorsFilter.validate_parameter("fr:departement:99") == [
            "fr:departement:99"
        ]

    def test_dataset_service_targets_geozones_field(self):
        filters = {"geozone_with_ancestors": ["fr:departement:29", "country:fr"]}
        DatasetService.format_filters(filters)
        assert filters == {"geozones": ["fr:departement:29", "country:fr"]}
