from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import (
    GeoLevelFactory,
    GeoZoneFactory,
    SpatialCoverageFactory,
)
from udata.core.spatial.models import spatial_granularities
from udata.core.spatial.tasks import compute_geozones_metrics
from udata.tests.api import APITestCase
from udata.tests.api.test_datasets_api import SAMPLE_GEOM
from udata.tests.features.territories import (
    TerritoriesSettings,
    create_geozones_fixtures,
)
from udata.utils import faker


class SpatialApiTest(APITestCase):
    modules = []

    def test_zones_api_one(self):
        zone = GeoZoneFactory()

        url = url_for("api.zones", ids=[zone.id])
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json["features"]), 1)

        feature = response.json["features"][0]
        self.assertEqual(feature["type"], "Feature")
        self.assertEqual(feature["id"], zone.id)

        properties = feature["properties"]
        self.assertEqual(properties["name"], zone.name)
        self.assertEqual(properties["code"], zone.code)
        self.assertEqual(properties["level"], zone.level)
        self.assertEqual(properties["uri"], zone.uri)

    def test_zones_api_many(self):
        zones = [GeoZoneFactory() for _ in range(3)]

        url = url_for("api.zones", ids=zones)
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json["features"]), len(zones))

        for zone, feature in zip(zones, response.json["features"]):
            self.assertEqual(feature["type"], "Feature")
            self.assertEqual(feature["id"], zone.id)

            properties = feature["properties"]
            self.assertEqual(properties["name"], zone.name)
            self.assertEqual(properties["code"], zone.code)
            self.assertEqual(properties["level"], zone.level)
            self.assertEqual(properties["uri"], zone.uri)

    def test_suggest_zones_on_name(self):
        """It should suggest zones based on its name"""
        for i in range(4):
            GeoZoneFactory(name="name-test-{0}".format(i) if i % 2 else faker.word())

        response = self.get(url_for("api.suggest_zones"), qs={"q": "name-test", "size": "5"})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn("id", suggestion)
            self.assertIn("name", suggestion)
            self.assertIn("code", suggestion)
            self.assertIn("uri", suggestion)
            self.assertIn("level", suggestion)
            self.assertIn("name-test", suggestion["name"])

    def test_suggest_zones_on_id(self):
        """It should suggest zones based on its id"""
        zone = GeoZoneFactory()
        for _ in range(2):
            GeoZoneFactory()

        response = self.get(url_for("api.suggest_zones"), qs={"q": zone.id})
        self.assert200(response)

        self.assertEqual(response.json[0]["id"], zone["id"])

    def test_suggest_zones_sorted(self):
        """It should suggest zones based on its name"""
        country_level = GeoLevelFactory(id="country", name="country", admin_level=10)
        region_level = GeoLevelFactory(id="region", name="region", admin_level=20)
        country_zone = GeoZoneFactory(name="name-test-country", level=country_level.id)
        region_zone = GeoZoneFactory(name="name-test-region", level=region_level.id)

        response = self.get(url_for("api.suggest_zones"), qs={"q": "name-test", "size": "5"})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)
        self.assertEqual((response.json[0]["id"]), country_zone.id)
        self.assertEqual((response.json[1]["id"]), region_zone.id)

    def test_suggest_zones_on_code(self):
        """It should suggest zones based on its code"""
        for i in range(4):
            GeoZoneFactory(code="code-test-{0}".format(i) if i % 2 else faker.word())

        response = self.get(url_for("api.suggest_zones"), qs={"q": "code-test", "size": "5"})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn("id", suggestion)
            self.assertIn("name", suggestion)
            self.assertIn("code", suggestion)
            self.assertIn("level", suggestion)
            self.assertIn("uri", suggestion)
            self.assertIn("code-test", suggestion["code"])

    def test_suggest_zones_no_match(self):
        """It should not provide zones suggestions if no match"""
        for i in range(3):
            GeoZoneFactory(name=5 * "{0}".format(i), code=3 * "{0}".format(i))

        response = self.get(url_for("api.suggest_zones"), qs={"q": "xxxxxx", "size": "5"})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_zones_unicode(self):
        """It should suggest zones based on its name"""
        for i in range(4):
            GeoZoneFactory(name="name-testé-{0}".format(i) if i % 2 else faker.word())

        response = self.get(url_for("api.suggest_zones"), qs={"q": "name-testé", "size": "5"})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn("id", suggestion)
            self.assertIn("name", suggestion)
            self.assertIn("code", suggestion)
            self.assertIn("level", suggestion)
            self.assertIn("uri", suggestion)
            self.assertIn("name-testé", suggestion["name"])

    def test_suggest_zones_empty(self):
        """It should not provide zones suggestion if no data is present"""
        response = self.get(url_for("api.suggest_zones"), qs={"q": "xxxxxx", "size": "5"})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_spatial_levels(self):
        levels = [GeoLevelFactory() for _ in range(3)]

        response = self.get(url_for("api.spatial_levels"))
        self.assert200(response)
        self.assertEqual(len(response.json), len(levels))

    def test_spatial_granularities(self):
        levels = [GeoLevelFactory() for _ in range(3)]

        response = self.get(url_for("api.spatial_granularities"))
        self.assert200(response)
        self.assertEqual(len(response.json), len(levels) + 2)

    def test_zone_datasets_empty(self):
        paca, bdr, arles = create_geozones_fixtures()
        response = self.get(url_for("api.zone_datasets", id=paca.id))
        self.assert200(response)
        self.assertEqual(response.json, [])

    def test_zone_datasets(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id))
        self.assert200(response)
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id), qs={"size": 2})
        self.assert200(response)
        self.assertEqual(len(response.json), 2)

    def test_zone_datasets_with_dynamic(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id), qs={"dynamic": 1})
        self.assert200(response)
        # No dynamic datasets given that the setting is deactivated by default.
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_dynamic_and_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id), qs={"dynamic": 1, "size": 2})
        self.assert200(response)
        # No dynamic datasets given that the setting is deactivated by default.
        self.assertEqual(len(response.json), 2)

    def test_coverage_empty(self):
        GeoLevelFactory(id="top")
        response = self.get(url_for("api.spatial_coverage", level="top"))
        self.assert200(response)
        self.assertEqual(
            response.json,
            {
                "type": "FeatureCollection",
                "features": [],
            },
        )

    def test_coverage_datasets_count(self):
        GeoLevelFactory(id="fr:commune")
        paris = GeoZoneFactory(
            id="fr:commune:75056", level="fr:commune", name="Paris", code="75056"
        )
        arles = GeoZoneFactory(
            id="fr:commune:13004", level="fr:commune", name="Arles", code="13004"
        )

        for _ in range(3):
            DatasetFactory(spatial=SpatialCoverageFactory(zones=[paris.id]))
        for _ in range(2):
            DatasetFactory(spatial=SpatialCoverageFactory(zones=[arles.id]))

        compute_geozones_metrics()

        response = self.get(url_for("api.spatial_coverage", level="fr:commune"))
        self.assert200(response)
        self.assertEqual(response.json["features"][0]["id"], "fr:commune:13004")
        self.assertEqual(response.json["features"][0]["properties"]["datasets"], 2)
        self.assertEqual(response.json["features"][1]["id"], "fr:commune:75056")
        self.assertEqual(response.json["features"][1]["properties"]["datasets"], 3)


class SpatialTerritoriesApiTest(APITestCase):
    modules = []
    settings = TerritoriesSettings

    def test_zone_datasets_with_dynamic_and_setting(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id), qs={"dynamic": 1})
        self.assert200(response)
        # No dynamic datasets given that they are added by udata-front extension.
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_dynamic_and_setting_and_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            DatasetFactory(
                organization=organization, spatial=SpatialCoverageFactory(zones=[paca.id])
            )

        response = self.get(url_for("api.zone_datasets", id=paca.id), qs={"dynamic": 1, "size": 2})
        self.assert200(response)
        # No dynamic datasets given that they are added by udata-front extension.
        self.assertEqual(len(response.json), 2)


class DatasetsSpatialAPITest(APITestCase):
    modules = []

    def test_create_spatial_zones(self):
        paca, _, _ = create_geozones_fixtures()
        granularity = spatial_granularities[0][0]
        data = DatasetFactory.as_dict()
        data["spatial"] = {
            "zones": [paca.id],
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("api.datasets"), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual([str(z) for z in dataset.spatial.zones], [paca.id])
        self.assertEqual(dataset.spatial.geom, None)
        self.assertEqual(dataset.spatial.granularity, granularity)

    def test_create_spatial_geom(self):
        granularity = spatial_granularities[0][0]
        data = DatasetFactory.as_dict()
        data["spatial"] = {
            "geom": SAMPLE_GEOM,
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("api.datasets"), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual(dataset.spatial.zones, [])
        self.assertEqual(dataset.spatial.geom, SAMPLE_GEOM)
        self.assertEqual(dataset.spatial.granularity, granularity)

    def test_cannot_create_both_geom_and_zones(self):
        paca, _, _ = create_geozones_fixtures()

        granularity = spatial_granularities[0][0]
        data = DatasetFactory.as_dict()
        data["spatial"] = {
            "zones": [paca.id],
            "geom": SAMPLE_GEOM,
            "granularity": granularity,
        }
        self.login()

        response = self.post(url_for("api.datasets"), data)
        self.assert400(response)
        self.assertEqual(Dataset.objects.count(), 0)
