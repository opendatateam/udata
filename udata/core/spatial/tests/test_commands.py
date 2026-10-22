import json
from tempfile import NamedTemporaryFile
from unittest import mock

from udata.core.dataset.factories import DatasetFactory
from udata.core.spatial.constants import DETECTED_ZONES_KEY
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import GeoZone, SpatialCoverage, get_zone_bboxes, zone_bboxes
from udata.tests.api import DBTestCase

LEVELS = [{"id": "fr:departement", "label": "Département"}]


def zone_record(**kwargs):
    return {
        "_id": "fr:departement:32",
        "nom": "Gers",
        "level": "fr:departement",
        "codeINSEE": "32",
        "uri": "http://id.insee.fr/geo/departement/32",
        **kwargs,
    }


class LoadGeozonesBboxCommandTest(DBTestCase):
    def _load(self, zones):
        paths = []
        for content in (zones, LEVELS):
            with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(content, f)
                paths.append(f.name)
        return self.cli("spatial", "load", *paths)

    def test_load_persists_bbox(self):
        result = self._load([zone_record(bbox=[-0.2821, 43.3108, 1.2032, 44.08])])

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            GeoZone.objects.get(id="fr:departement:32").bbox, [-0.2821, 43.3108, 1.2032, 44.08]
        )

    def test_load_without_bbox_keeps_existing_bbox(self):
        GeoZoneFactory(id="fr:departement:32", level="fr:departement", bbox=[0.0, 0.0, 1.0, 1.0])

        result = self._load([zone_record()])

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(GeoZone.objects.get(id="fr:departement:32").bbox, [0.0, 0.0, 1.0, 1.0])

    def test_load_refreshes_bboxes_cache(self):
        # warm the cache before the zone has a bbox
        get_zone_bboxes()
        self.assertNotIn("fr:departement:32", zone_bboxes)

        self._load([zone_record(bbox=[0.0, 0.0, 1.0, 1.0])])

        self.assertEqual(zone_bboxes["fr:departement:32"], [0.0, 0.0, 1.0, 1.0])


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
