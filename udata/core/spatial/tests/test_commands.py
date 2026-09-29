import json
from tempfile import NamedTemporaryFile
from unittest import mock

from udata.core.dataset.factories import DatasetFactory
from udata.core.spatial.constants import DETECTED_ZONES_KEY
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import SpatialCoverage, get_zone_bboxes, zone_bboxes
from udata.tests.api import DBTestCase


class LoadGeozonesBboxesCommandTest(DBTestCase):
    def _write_bboxes_file(self, bboxes):
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(bboxes, f)
            return f.name

    def test_load_geozones_bboxes(self):
        zone = GeoZoneFactory()
        other_zone = GeoZoneFactory()
        path = self._write_bboxes_file(
            {
                zone.id: [0.0, 0.0, 1.0, 1.0],
                "unknown:zone:id": [2.0, 2.0, 3.0, 3.0],
            }
        )

        result = self.cli(f"spatial load-geozones-bboxes {path}")

        self.assertEqual(result.exit_code, 0)

        zone.reload()
        self.assertEqual(zone.bbox, [0.0, 0.0, 1.0, 1.0])

        other_zone.reload()
        self.assertFalse(other_zone.bbox)

    def test_load_geozones_bboxes_refreshes_cache(self):
        zone = GeoZoneFactory()
        path = self._write_bboxes_file({zone.id: [0.0, 0.0, 1.0, 1.0]})

        # warm the cache before the zone has a bbox
        get_zone_bboxes()
        self.assertNotIn(zone.id, zone_bboxes)

        self.cli(f"spatial load-geozones-bboxes {path}")

        self.assertEqual(zone_bboxes[zone.id], [0.0, 0.0, 1.0, 1.0])


RECTANGLE_GEOM = {
    "type": "MultiPolygon",
    "coordinates": [[[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]]],
}


class DetectZonesCommandTest(DBTestCase):
    def _dataset_with_geom_without_detection(self):
        # bypass signals to mimic a dataset created before detection existed
        dataset = DatasetFactory()
        type(dataset).objects(id=dataset.id).update(
            set__spatial=SpatialCoverage(geom=RECTANGLE_GEOM)
        )
        dataset.reload()
        return dataset

    def test_detects_zones_for_existing_datasets_with_geom(self):
        zone = GeoZoneFactory(bbox=[0.0, 0.0, 10.0, 10.0])
        with_geom = self._dataset_with_geom_without_detection()
        without_geom = DatasetFactory()

        with mock.patch("udata.core.spatial.tasks.reindex") as reindex:
            result = self.cli("spatial detect-zones")

        self.assertEqual(result.exit_code, 0)
        with_geom.reload()
        without_geom.reload()
        self.assertEqual(with_geom.extras.get(DETECTED_ZONES_KEY), [zone.id])
        self.assertNotIn(DETECTED_ZONES_KEY, without_geom.extras)
        reindex.delay.assert_called_once_with("Dataset", str(with_geom.id))
