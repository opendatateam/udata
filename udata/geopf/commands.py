import click

from udata.commands import cli, exit_with_error
from udata.core.dataset.models import Dataset
from udata.core.user.models import User

from .auth import resolve_access_token
from .client import GeopfClient, GeopfError, GeopfReauthRequired
from .tasks import fiche_url, pull_offerings_from_geopf, push_resource_to_geopf, sync_metadata


@cli.group("geopf")
def grp():
    """Géoplateforme integration operations"""
    pass


def _require_datastore_id(datastore_id: str | None) -> str:
    if not datastore_id:
        exit_with_error("Provide --datastore-id")
    return datastore_id


def _check_credentials(user_id: str | None, token: str | None) -> None:
    """Validate --user-id/--token CLI options: exactly one, and if --user-id, that the
    user exists."""
    if bool(user_id) == bool(token):
        exit_with_error("Provide exactly one of --user-id or --token")
    if user_id and not User.objects(id=user_id).first():
        exit_with_error(f"User {user_id} not found")


def _resolve_token_option(user_id: str | None, token: str | None) -> str:
    """Resolve --user-id/--token CLI options to a usable access token."""
    _check_credentials(user_id, token)
    if token:
        return token
    user = User.objects.get(id=user_id)
    try:
        return resolve_access_token(user=user)
    except GeopfReauthRequired as e:
        exit_with_error(str(e))


user_id_option = click.option(
    "--user-id", help="Act as this user, using their stored geopf token (refreshed as needed)"
)
token_option = click.option(
    "--token", help="Act with this raw access token, bypassing any stored token"
)
datastore_id_option = click.option("--datastore-id", help="Datastore to push into")


@grp.command("push-resource")
@click.argument("dataset_id")
@click.argument("resource_id")
@user_id_option
@token_option
@datastore_id_option
def push_resource(dataset_id, resource_id, user_id, token, datastore_id):
    """Push a GPKG resource to Géoplateforme (runs synchronously)."""
    _check_credentials(user_id, token)
    datastore_id = _require_datastore_id(datastore_id)
    push_resource_to_geopf(dataset_id, resource_id, user_id, datastore_id, token)


@grp.command("push-metadata")
@click.argument("dataset_id")
@user_id_option
@token_option
@datastore_id_option
def push_metadata(dataset_id, user_id, token, datastore_id):
    """Sync metadata for a dataset to Géoplateforme."""
    access_token = _resolve_token_option(user_id, token)
    datastore_id = _require_datastore_id(datastore_id)

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        exit_with_error(f"Dataset {dataset_id} not found")

    try:
        client = GeopfClient(token=access_token, datastore_id=datastore_id)
        metadata_id = sync_metadata(dataset, client)
    except GeopfError as e:
        exit_with_error(str(e))

    click.echo(f"metadata={metadata_id}")
    click.echo(f"fiche={fiche_url(datastore_id, dataset_id)}")


@grp.command("pull-offerings")
@click.argument("dataset_id")
@user_id_option
@token_option
def pull_offerings(dataset_id, user_id, token):
    """Pull Géoplateforme offerings into resources for a dataset (runs synchronously)."""
    _check_credentials(user_id, token)
    n = pull_offerings_from_geopf(dataset_id, user_id, token)
    click.echo(f"pulled={n} offerings for dataset {dataset_id}")
