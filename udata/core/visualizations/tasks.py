from udata.core import storages
from udata.tasks import get_logger, job

from .models import Chart

log = get_logger(__name__)


@job("purge-visualizations")
def purge_visualizations(self) -> None:
    """Purge permanently deleted chart visualizations and their image files"""
    for chart in Chart.objects(deleted_at__ne=None):
        log.info(f"Purging visualization {chart}")
        # Remove chart's image in all sizes
        if chart.image.filename is not None:
            storage = storages.images
            storage.delete(chart.image.filename)
            storage.delete(chart.image.original)
            for key, value in chart.image.thumbnails.items():
                storage.delete(value)
        chart.delete()
