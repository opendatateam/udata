from urllib.parse import urlencode

from flask import Blueprint, current_app
from udata.app import cache

from udata_gouvfr import theme
from udata_gouvfr.frontend import template_hook

import requests

blueprint = Blueprint('schema', __name__,)


def validata_url(resource, schema_url=None):
    base = current_app.config.get('SCHEMA_GOUVFR_VALIDATA_URL')
    if schema_url is None:
        schema_path = {'schema_name': f"schema-datagouvfr.{resource['schema'].get('name')}"}
    else:
        schema_path = {"schema_url": schema_url}

    params = {
        'input': 'url',
        'url': resource.url,
    }

    query = urlencode({**params, **schema_path})

    return f"{base}/table-schema?{query}"


def is_table_schema(schemas, current_schema):
    return any([s['name'] == current_schema and
                s['schema_type'] == 'tableschema' for s in (schemas or [])])


def get_schema_url(schemas, current_schema, current_schema_version):
    if schemas:
        for schema in schemas:
            if schema['name'] == current_schema:
                for version in schema['versions']:
                    if version['version_name'] == current_schema_version:
                        return version['schema_url']


@cache.memoize(timeout=600)
def load_catalog():
    r = requests.get(current_app.config.get('SCHEMA_CATALOG_URL'))
    r.raise_for_status()
    if 'schemas' in r.json():
        return r.json()['schemas']


def resource_has_schema(ctx):
    return ctx.get('resource') and ctx['resource'].schema


def dataset_has_schema(ctx):
    if ctx.get('dataset') is None:
        return False
    return any([r.schema is not None for r in ctx['dataset'].resources])


@template_hook('dataset.resource.card.extra-buttons', when=resource_has_schema)
def resource_schema_details(ctx):
    schemas = load_catalog()
    resource = ctx['resource']

    authorize_validation = is_table_schema(schemas, resource.schema['name'])

    validation_url = None

    if authorize_validation:
        schema_url = None
        if 'version' in resource.schema:
            schema_url = get_schema_url(
                schemas,
                resource.schema['name'],
                resource.schema['version'],
            )
        validation_url = validata_url(resource, schema_url)

    documentation_url = f"https://schema.data.gouv.fr/{resource.schema['name']}/latest.html"

    return theme.render(
        'dataset/resource/schema-button.html',
        resource=resource,
        documentation_url=documentation_url,
        validation_url=validation_url,
        authorize_validation=authorize_validation
    )
