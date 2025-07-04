import json
import logging
from importlib.resources import files

import jsonschema
import mongoengine
import requests
from flask import current_app

from udata.commands import error, success
from udata.models import Dataset, Reuse
from udata.tasks import job
from udata.uris import validate

log = logging.getLogger(__name__)


def recommendations_clean():
    nb_datasets = Dataset.objects.filter(
        **{
            "extras__recommendations__exists": True,
        }
    ).update(
        **{
            "unset__extras__recommendations": True,
            "unset__extras__recommendations-reuses": True,
            "unset__extras__recommendations:sources": True,
        }
    )
    success(f"Removed recommendations from {nb_datasets} dataset(s)")


schema_path = files("udata").joinpath("schemas", "recommendations.json")


def get_recommendations_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    with schema_path.open() as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)

    return data


def get_unique_recommendations(recos):
    """
    This function returns a list of unique recos, based on the `id` key.
    The first unique element found is kept, following ones are ignored.
    Thus you should order the list accordingly before applying this function.
    """
    ids_seen = set()
    unique_recos = []
    for reco in recos:
        if reco["id"] not in ids_seen:
            ids_seen.add(reco["id"])
            unique_recos.append(reco)
    return unique_recos


def get_dataset(id_or_slug):
    obj = Dataset.objects(slug=id_or_slug).first()
    return obj or Dataset.objects.get(id=id_or_slug)


def get_reuse(id_or_slug):
    obj = Reuse.objects(slug=id_or_slug).first()
    return obj or Reuse.objects.get(id=id_or_slug)


def process_source(source, recommendations_data):
    for dataset in recommendations_data:
        process_dataset(source, dataset)


def process_dataset(source, dataset):
    try:
        target_dataset = get_dataset(dataset["id"])
    except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
        error(f"Dataset {dataset['id']} not found")
        return

    log.info(f"Processing recommendations for dataset {dataset['id']}")
    valid_recos_datasets = []
    valid_recos_reuses = []
    valid_recos_externals = []
    for reco in dataset["recommendations"]:
        # default type is `dataset` for retrocompat
        reco_type = reco.get("type", "dataset")
        if reco_type == "dataset":
            try:
                reco_dataset_obj = get_dataset(reco["id"])
                if reco_dataset_obj.id == target_dataset.id:
                    continue
                valid_recos_datasets.append(
                    {
                        "id": str(reco_dataset_obj.id),
                        "score": reco["score"],
                        "source": source,
                    }
                )
            except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
                error(f"Recommended dataset {reco['id']} not found")
                continue
        elif reco_type == "reuse":
            try:
                reuse = get_reuse(reco["id"])
                valid_recos_reuses.append(
                    {
                        "id": str(reuse.id),
                        "score": reco["score"],
                        "source": source,
                    }
                )
            except (Reuse.DoesNotExist, mongoengine.errors.ValidationError):
                error(f"Recommended reuse {reco['id']} not found")
                continue
        elif reco_type == "external":
            try:
                external = validate(reco["id"])
                valid_recos_externals.append(
                    {
                        "id": external,
                        "score": reco["score"],
                        "source": source,
                        "messages": reco["messages"],
                    }
                )
            except ValueError:
                error(f"Recommended external {reco['id']} is not a valid url")
                continue
        else:
            error(f"Unknown recommendation type {reco_type}")
            continue

    if len(valid_recos_datasets) or len(valid_recos_reuses) or len(valid_recos_externals):
        new_sources = set(target_dataset.extras.get("recommendations:sources", []))
        new_sources.add(source)
        target_dataset.extras["recommendations:sources"] = list(new_sources)

    if len(valid_recos_datasets):
        success(
            f"Found {len(valid_recos_datasets)} new dataset recommendations for dataset {dataset['id']}"
        )

        merged_recommendations = valid_recos_datasets + target_dataset.extras.get(
            "recommendations", []
        )
        unique_recommendations = get_unique_recommendations(merged_recommendations)
        new_recommendations = sorted(unique_recommendations, key=lambda k: k["score"], reverse=True)

        target_dataset.extras["recommendations"] = new_recommendations

    if len(valid_recos_reuses):
        success(
            f"Found {len(valid_recos_reuses)} new reuse recommendations for dataset {dataset['id']}"
        )

        merged_recommendations = valid_recos_reuses + target_dataset.extras.get(
            "recommendations-reuses", []
        )
        unique_recommendations = get_unique_recommendations(merged_recommendations)
        new_recommendations = sorted(unique_recommendations, key=lambda k: k["score"], reverse=True)

        target_dataset.extras["recommendations-reuses"] = new_recommendations

    if len(valid_recos_externals):
        success(
            f"Found {len(valid_recos_externals)} new external recommendations for dataset {dataset['id']}"
        )

        merged_recommendations = valid_recos_externals + target_dataset.extras.get(
            "recommendations-externals", []
        )
        unique_recommendations = get_unique_recommendations(merged_recommendations)
        new_recommendations = sorted(unique_recommendations, key=lambda k: k["score"], reverse=True)

        target_dataset.extras["recommendations-externals"] = new_recommendations

    if len(valid_recos_datasets) or len(valid_recos_reuses) or len(valid_recos_externals):
        target_dataset.save()
    else:
        error(f"No recommendations found for dataset {dataset['id']}")


def recommendations_add(sources, should_clean):
    if should_clean:
        log.info("Cleaning up dataset recommendations")
        recommendations_clean()

    for source, url in sources.items():
        log.info(f"Fetching dataset recommendations from {url}, source {source}")
        process_source(source, get_recommendations_data(url))


@job("recommendations-clean")
def run_recommendations_clean(self):
    recommendations_clean()


@job("recommendations-add")
def run_recommendations_add(self, should_clean=True):
    should_clean = should_clean in [True, "true", "True"]
    sources = current_app.config.get("RECOMMENDATIONS_SOURCES", {})

    recommendations_add(sources, should_clean)
