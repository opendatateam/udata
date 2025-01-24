from flask import current_app

from udata.core.metrics.signals import on_site_metrics_computed
from udata.models import Site
from udata.tasks import job


@job("compute-site-metrics")
def compute_site_metrics(self):
    site = Site.objects(id=current_app.config["SITE_ID"]).first()
    site.count_users()
    site.count_org()
    site.count_datasets()
    site.count_resources()
    site.count_reuses()
    site.count_dataservices()
    site.count_followers()
    site.count_discussions()
    site.count_harvesters()
    site.count_max_dataset_followers()
    site.count_max_dataset_reuses()
    site.count_max_reuse_datasets()
    site.count_max_reuse_followers()
    site.count_max_org_followers()
    site.count_max_org_reuses()
    site.count_max_org_datasets()
    # Sending signal
    on_site_metrics_computed.send(site)
