from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.spatial.commands import load_zones
from udata.core.spatial.factories import GeoZoneFactory, SpatialCoverageFactory
from udata.core.spatial.models import GeoZone
from udata.tests.api import APITestCase


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

    def test_include_ancestors_expands_geozone(self):
        GeoZoneFactory(id="fr:departement:29", ancestors=["country:fr", "fr:region:53"])
        params = {"geozone": "fr:departement:29", "include_geozone_ancestors": True}
        assert DatasetSearch.prepare_filters(params) == {
            "geozone": ["fr:departement:29", "country:fr", "fr:region:53"]
        }

    def test_geozone_untouched_without_flag(self):
        GeoZoneFactory(id="fr:departement:29", ancestors=["country:fr", "fr:region:53"])
        params = {"geozone": "fr:departement:29", "include_geozone_ancestors": False}
        assert DatasetSearch.prepare_filters(params) == {"geozone": "fr:departement:29"}

    def test_include_ancestors_keeps_unknown_zone(self):
        params = {"geozone": "fr:departement:99", "include_geozone_ancestors": True}
        assert DatasetSearch.prepare_filters(params) == {"geozone": "fr:departement:99"}

    def test_include_ancestors_without_geozone_is_dropped(self):
        assert DatasetSearch.prepare_filters({"include_geozone_ancestors": True}) == {}

    def test_mongo_fallback_includes_ancestors(self):
        region = GeoZoneFactory(id="fr:region:53")
        departement = GeoZoneFactory(id="fr:departement:29", ancestors=[region.id])
        elsewhere = GeoZoneFactory(id="fr:departement:75")
        DatasetFactory(title="Département", spatial=SpatialCoverageFactory(zones=[departement]))
        DatasetFactory(title="Région", spatial=SpatialCoverageFactory(zones=[region]))
        DatasetFactory(title="Ailleurs", spatial=SpatialCoverageFactory(zones=[elsewhere]))

        response = self.get(
            "/api/2/datasets/search/?geozone=fr:departement:29&include_geozone_ancestors=true"
        )
        self.assert200(response)
        assert {d["title"] for d in response.json["data"]} == {"Département", "Région"}


class IncludeDetectedGeozonesParamTest(APITestCase):
    def test_flag_is_parsed_as_a_boolean(self):
        from udata.core.dataset.search import DatasetSearch

        parser = DatasetSearch.as_request_parser(store_missing=False)
        for raw, expected in (("true", True), ("false", False)):
            with self.app.test_request_context(f"/?include_detected_geozones={raw}"):
                self.assertIs(parser.parse_args()["include_detected_geozones"], expected)
