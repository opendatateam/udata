"""
Delete all Chart visualizations: the declarative config fields are
removed from the model and charts are a hidden beta, so existing documents are
dropped rather than migrated.
"""

import logging

from udata.core.visualizations.models import Chart

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Deleting all Chart visualizations...")

    deleted_count = 0
    for chart in Chart.objects.no_cache().all():
        chart.delete()
        deleted_count += 1

    log.info(f"Deleted {deleted_count} charts")
