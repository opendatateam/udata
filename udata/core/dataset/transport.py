import requests
from flask import current_app

from udata.commands import error, success
from udata.models import Dataset
from udata.tasks import job


def process_dataset(dataset):
    target_dataset = Dataset.objects(id=dataset["datagouv_id"]).first()
    if not target_dataset:
        error(f"Dataset {dataset['id']} not found")
        return
    target_dataset.extras["transport:url"] = dataset["page_url"]
    target_dataset.save()


def clear_datasets():
    nb_datasets = Dataset.objects.filter(
        **{
            "extras__transport:url__exists": True,
        }
    ).update(
        **{
            "unset__extras__transport:url": True,
        }
    )
    success(f"Removed transport:url from {nb_datasets} dataset(s)")


@job("map-transport-datasets")
def map_transport_datasets(self):
    source = current_app.config.get("TRANSPORT_DATASETS_URL", None)
    if not source:
        error("TRANSPORT_DATASETS_URL variable must be set.")
        return

    response = requests.get(source)
    if response.status_code != 200:
        error("Remote platform unreachable.")
        return
    results_list = response.json()
    clear_datasets()
    for dataset in results_list:
        process_dataset(dataset)
    success(f"Done. {len(results_list)} datasets mapped to transport")
