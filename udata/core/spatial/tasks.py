from celery.utils.log import get_task_logger

from udata.core.dataset.models import Dataset
from udata.core.spatial.models import GeoZone, zone_bboxes
from udata.core.spatial.zone_detection import detect_zone, geom_to_bbox
from udata.tasks import job, task

log = get_task_logger(__name__)


@job("compute-geozones-metrics")
def compute_geozones_metrics(self):
    for geozone in GeoZone.objects.timeout(False):
        geozone.count_datasets()


@task(route="low.spatial")
def detect_and_write_zone(dataset_id):
    dataset = Dataset.objects(id=dataset_id).first()
    if dataset is None:
        return

    zone_ids = None
    # Zones and geom are mutually exclusive (SpatialCoverage.clean()), so an
    # explicit zones already covers this dataset -- nothing to detect.
    if dataset.spatial and dataset.spatial.geom and not dataset.spatial.zones:
        bbox = geom_to_bbox(dataset.spatial.geom)
        if bbox is not None:
            zone_ids = detect_zone(bbox, zone_bboxes)

    if zone_ids:
        log.info("Detected zone(s) %s for dataset %s", zone_ids, dataset_id)
        Dataset.objects(id=dataset_id).update(**{"set__extras__analysis:spatial:zones": zone_ids})
    else:
        # Covers "no match" as well as "no longer applicable" (geom cleared,
        # zones set explicitly, etc.) -- clears any stale previous match.
        # No-op (and harmless) if the key was never set.
        log.debug("No zone match for dataset %s", dataset_id)
        Dataset.objects(id=dataset_id).update(**{"unset__extras__analysis:spatial:zones": 1})


@Dataset.on_create.connect
def detect_zone_on_create(document, **kwargs):
    # on_create doesn't carry changed_fields, so guard on geom presence directly
    # (most datasets have no spatial data -- avoid dispatching a task for all of them).
    if document.spatial and document.spatial.geom:
        detect_and_write_zone.delay(str(document.id))


@Dataset.on_update.connect
def detect_zone_on_spatial_change(document, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if any(f == "spatial" or f.startswith("spatial.") for f in changed_fields):
        detect_and_write_zone.delay(str(document.id))
