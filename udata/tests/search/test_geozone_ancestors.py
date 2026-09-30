from udata.core.dataset.search import DatasetSearch
from udata.core.spatial.commands import load_zones
from udata.core.spatial.factories import GeoZoneFactory
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
