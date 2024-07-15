from udata.core.spatial.models import GeoZone
from udata.tasks import job


@job("compute-geozones-metrics")
def compute_geozones_metrics(self):
    for geozone in GeoZone.objects.timeout(False):
        geozone.count_datasets()
