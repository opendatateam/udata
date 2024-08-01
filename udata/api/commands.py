import logging
import os

import click
from flask import current_app, json
from flask_restx import schemas

from udata.api import api
from udata.api.oauth2 import OAuth2Client
from udata.commands import cli, exit_with_error, success
from udata.models import User

log = logging.getLogger(__name__)


@cli.group("api")
def grp():
    """API related operations"""


def json_to_file(data, filename, pretty=False):
    """Dump JSON data to a file"""
    kwargs = dict(indent=4) if pretty else {}
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    dump = json.dumps(api.__schema__, **kwargs)
    with open(filename, "wb") as f:
        f.write(dump.encode("utf-8"))


@grp.command()
@click.argument("filename")
@click.option("-p", "--pretty", is_flag=True, help="Pretty print")
def swagger(filename, pretty):
    """Dump the swagger specifications"""
    json_to_file(api.__schema__, filename, pretty)


@grp.command()
@click.argument("filename")
@click.option("-p", "--pretty", is_flag=True, help="Pretty print")
@click.option("-u", "--urlvars", is_flag=True, help="Export query strings")
@click.option("-s", "--swagger", is_flag=True, help="Export Swagger specifications")
def postman(filename, pretty, urlvars, swagger):
    """Dump the API as a Postman collection"""
    data = api.as_postman(urlvars=urlvars, swagger=swagger)
    json_to_file(data, filename, pretty)


@grp.command()
def validate():
    """Validate the Swagger/OpenAPI specification with your config"""
    with current_app.test_request_context():
        schema = json.loads(json.dumps(api.__schema__))
    try:
        schemas.validate(schema)
        success("API specifications are valid")
    except schemas.SchemaValidationError as e:
        exit_with_error("API specifications are not valid", e)


@grp.command()
@click.option("-n", "--client-name", default="client-01", help="Client's name")
@click.option("-u", "--user-email", help="User's email")
@click.option(
    "--uri", multiple=True, default=["http://localhost:8080/login"], help="Client's redirect uri"
)
@click.option(
    "-g",
    "--grant-types",
    multiple=True,
    default=["authorization_code"],
    help="Client's grant types",
)
@click.option("-s", "--scope", default="default", help="Client's scope")
@click.option(
    "-r", "--response-types", multiple=True, default=["code"], help="Client's response types"
)
def create_oauth_client(client_name, user_email, uri, grant_types, scope, response_types):
    """Creates an OAuth2Client instance in DB"""
    user = User.objects(email=user_email).first()
    if user is None:
        exit_with_error("No matching user to email")

    client = OAuth2Client.objects.create(
        name=client_name,
        owner=user,
        grant_types=grant_types,
        scope=scope,
        response_types=response_types,
        redirect_uris=uri,
    )

    click.echo(f"New OAuth client: {client.name}")
    click.echo(f"Client's ID {client.id}")
    click.echo(f"Client's secret {client.secret}")
    click.echo(f"Client's grant_types {client.grant_types}")
    click.echo(f"Client's response_types {client.response_types}")
    click.echo(f"Client's URI {client.redirect_uris}")
