from udata.core.dataset.factories import DatasetFactory
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import SpatialCoverage
from udata.tests.api import DBTestCase

RECTANGLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [[[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]]],
}


class DetectZoneOnSpatialChangeTest(DBTestCase):
    def test_writes_matching_zone_on_geom_save(self):
        zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory()

        dataset.spatial = SpatialCoverage(geom=RECTANGLE_GEOM)
        dataset.save()

        dataset.reload()
        self.assertEqual(dataset.extras.get("analysis:spatial:zones"), [zone.id])

    def test_writes_matching_zone_on_creation_with_geom(self):
        # dataset created with geom already set in a single save -- fires
        # Dataset.on_create, not on_update (e.g. harvesters do exactly this)
        zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory(spatial=SpatialCoverage(geom=RECTANGLE_GEOM))

        dataset.reload()
        self.assertEqual(dataset.extras.get("analysis:spatial:zones"), [zone.id])

    def test_writes_matching_zone_on_in_place_geom_mutation(self):
        zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory(spatial=SpatialCoverage())

        # in-place subfield mutation produces changed_fields=['spatial.geom'],
        # not ['spatial'] -- both forms must trigger detection
        dataset.spatial.geom = RECTANGLE_GEOM
        dataset.save()

        dataset.reload()
        self.assertEqual(dataset.extras.get("analysis:spatial:zones"), [zone.id])

    def test_writes_all_tied_zones_on_exact_tie(self):
        # e.g. a region and a department sharing identical geometry (DOM-TOM)
        region = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        departement = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory()

        dataset.spatial = SpatialCoverage(geom=RECTANGLE_GEOM)
        dataset.save()

        dataset.reload()
        self.assertEqual(
            sorted(dataset.extras.get("analysis:spatial:zones")),
            sorted([region.id, departement.id]),
        )

    def test_no_match_below_threshold(self):
        GeoZoneFactory(bbox=[100.0, 100.0, 110.0, 110.0])
        dataset = DatasetFactory()

        dataset.spatial = SpatialCoverage(geom=RECTANGLE_GEOM)
        dataset.save()

        dataset.reload()
        # no write on first pass, to avoid noise for datasets that never match
        self.assertNotIn("analysis:spatial:zones", dataset.extras)

    def test_no_match_clears_stale_match(self):
        matching_zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory()

        dataset.spatial = SpatialCoverage(geom=RECTANGLE_GEOM)
        dataset.save()
        dataset.reload()
        self.assertEqual(dataset.extras.get("analysis:spatial:zones"), [matching_zone.id])

        # geometry moves away from the matching zone -- stale match must be cleared
        dataset.spatial.geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[200.0, 200.0], [210.0, 200.0], [210.0, 210.0], [200.0, 210.0], [200.0, 200.0]]]
            ],
        }
        dataset.save()

        dataset.reload()
        self.assertNotIn("analysis:spatial:zones", dataset.extras)

    def test_clearing_geom_for_explicit_zones_clears_stale_match(self):
        matching_zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory()

        dataset.spatial = SpatialCoverage(geom=RECTANGLE_GEOM)
        dataset.save()
        dataset.reload()
        self.assertEqual(dataset.extras.get("analysis:spatial:zones"), [matching_zone.id])

        # geom cleared and an explicit zone set instead, in the same save --
        # the inferred match is no longer applicable and must be cleared
        explicit_zone = GeoZoneFactory()
        dataset.spatial.geom = None
        dataset.spatial.zones = [explicit_zone]
        dataset.save()

        dataset.reload()
        self.assertNotIn("analysis:spatial:zones", dataset.extras)

    def test_dataset_with_explicit_zones_is_left_untouched(self):
        zone = GeoZoneFactory()
        dataset = DatasetFactory(spatial=SpatialCoverage(zones=[zone]))

        # trigger another (non-spatial) change; on_update fires but spatial
        # itself didn't change, and zones+geom are mutually exclusive anyway
        dataset.title = "updated title"
        dataset.save()

        dataset.reload()
        self.assertNotIn("analysis:spatial:zones", dataset.extras)

    def test_unrelated_field_change_does_not_trigger_detection(self):
        GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        dataset = DatasetFactory()
        dataset.title = "updated title"
        dataset.save()

        dataset.reload()
        self.assertNotIn("analysis:spatial:zones", dataset.extras)
