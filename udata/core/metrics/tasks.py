import logging
import time
from functools import wraps
from typing import Dict, List

import requests
from flask import current_app

from udata.core.dataservices.models import Dataservice
from udata.core.metrics.signals import on_site_metrics_computed
from udata.models import CommunityResource, Dataset, Organization, Reuse, Site, db
from udata.tasks import job

log = logging.getLogger(__name__)


def log_timing(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        # Better log if we're using Python 3.9
        name = func.__name__
        model = name.removeprefix("update_") if hasattr(name, "removeprefix") else name

        log.info(f"Processing {model}…")
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        total_time = time.perf_counter() - start_time
        log.info(f"Done in {total_time:.4f} seconds.")
        return result

    return timeit_wrapper


def save_model(model: db.Document, model_id: str, metrics: Dict[str, int]) -> None:
    try:
        result = model.objects(id=model_id).update(
            **{f"set__metrics__{key}": value for key, value in metrics.items()}
        )

        if result is None:
            log.debug(f"{model.__name__} not found", extra={"id": model_id})
    except Exception as e:
        log.exception(e)


def iterate_on_metrics(target: str, value_keys: List[str], page_size: int = 50) -> dict:
    """
    Yield all elements with not zero values for the keys inside `value_keys`.
    If you pass ['visit', 'download_resource'], it will do a `OR` and get
    metrics with one of the two values not zero.
    """
    yielded = set()

    for value_key in value_keys:
        url = f"{current_app.config['METRICS_API']}/{target}_total/data/"
        url += f"?{value_key}__greater=1&page_size={page_size}"

        with requests.Session() as session:
            while url is not None:
                r = session.get(url, timeout=10)
                r.raise_for_status()
                data = r.json()

                for row in data["data"]:
                    if row["__id"] not in yielded:
                        yielded.add(row["__id"])
                        yield row

                url = data["links"].get("next")


@log_timing
def update_resources_and_community_resources():
    for data in iterate_on_metrics("resources", ["download_resource"]):
        if data["dataset_id"] is None:
            save_model(
                CommunityResource,
                data["resource_id"],
                {
                    "views": data["download_resource"],
                },
            )
        else:
            Dataset.objects(resources__id=data["resource_id"]).update(
                **{"set__resources__$__metrics__views": data["download_resource"]}
            )


@log_timing
def update_datasets():
    for data in iterate_on_metrics("datasets", ["visit", "download_resource"]):
        save_model(
            Dataset,
            data["dataset_id"],
            {
                "views": data["visit"],
                "resources_downloads": data["download_resource"],
            },
        )


@log_timing
def update_dataservices():
    for data in iterate_on_metrics("dataservices", ["visit"]):
        save_model(
            Dataservice,
            data["dataservice_id"],
            {
                "views": data["visit"],
            },
        )


@log_timing
def update_reuses():
    for data in iterate_on_metrics("reuses", ["visit"]):
        save_model(Reuse, data["reuse_id"], {"views": data["visit"]})


@log_timing
def update_organizations():
    # We're currently using visit_dataset as global metric for an orga
    for data in iterate_on_metrics("organizations", ["visit_dataset"]):
        save_model(
            Organization,
            data["organization_id"],
            {
                "views": data["visit_dataset"],
            },
        )


def update_metrics_for_models():
    log.info("Starting…")
    update_datasets()
    update_resources_and_community_resources()
    update_dataservices()
    update_reuses()
    update_organizations()


@job("update-metrics", route="low.metrics")
def update_metrics(self):
    """Update udata objects metrics"""
    if not current_app.config["METRICS_API"]:
        log.error("You need to set METRICS_API to run update-metrics")
        exit(1)
    update_metrics_for_models()


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
    site.count_stock_metrics()
    # Sending signal
    on_site_metrics_computed.send(site)
