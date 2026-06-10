import click
from flask import current_app

from udata.commands import cli
from udata.core.dataset.models import Dataset

from .client import GeopfClient, GeopfError
from .tasks import sync_metadata, sync_services_for_dataset


@cli.group("geopf")
def grp():
    """Géoplateforme integration operations"""
    pass


@grp.command("sync-dataset")
@click.argument("dataset_id")
def sync_dataset(dataset_id):
    """Sync metadata for a dataset to Géoplateforme."""
    if not current_app.config.get("GEOPF_TOKEN") or not current_app.config.get(
        "GEOPF_DATASTORE_ID"
    ):
        raise click.ClickException("GEOPF_TOKEN or GEOPF_DATASTORE_ID not configured")

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise click.ClickException(f"Dataset {dataset_id} not found")

    try:
        client = GeopfClient()
        metadata_id = sync_metadata(dataset, client)
    except GeopfError as e:
        raise click.ClickException(str(e))

    datastore_id = current_app.config["GEOPF_DATASTORE_ID"]
    fiche_url = (
        f"https://cartes.gouv.fr/tableau-de-bord/entrepots/{datastore_id}/donnees/{dataset_id}"
    )
    click.echo(f"metadata={metadata_id}")
    click.echo(f"fiche={fiche_url}")


@grp.command("sync-services")
@click.argument("dataset_id")
def sync_services(dataset_id):
    """Sync GeoPortail offerings to resources for a dataset."""
    if not current_app.config.get("GEOPF_TOKEN") or not current_app.config.get(
        "GEOPF_DATASTORE_ID"
    ):
        raise click.ClickException("GEOPF_TOKEN or GEOPF_DATASTORE_ID not configured")

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise click.ClickException(f"Dataset {dataset_id} not found")

    try:
        client = GeopfClient()
        n = sync_services_for_dataset(dataset, client)
    except GeopfError as e:
        raise click.ClickException(str(e))

    click.echo(f"synced={n} offerings for dataset {dataset_id}")
