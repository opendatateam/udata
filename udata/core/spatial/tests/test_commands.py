import json
from tempfile import NamedTemporaryFile

from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import get_zone_bboxes, zone_bboxes
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
