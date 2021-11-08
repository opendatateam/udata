import logging
import json

import click
import requests

from udata.commands import cli
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory

log = logging.getLogger(__name__)


DATASET_SLUGS = [
    "barometre-des-resultats-de-laction-publique",
    "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret",
    "donnees-relatives-aux-personnes-vaccinees-contre-la-covid-19-1",
    "demandes-de-valeurs-foncieres",
    "logements-sociaux-et-bailleurs-par-region",
    "base-adresse-locale-de-la-commune-de-garein",
    "cuisses-de-grenouille-et-escargots-frogs-legs-and-snails",
    "marche-public-de-la-metropole-de-lyon",
    "defibrillateurs-presents-sur-la-commune-de-sixt-sur-aff-en-2018",
    "diagnostics-de-performance-energetique-pour-les-logements-par-habitation",
    "mairie-de-beynost-borne-de-recharge-pour-vehicules-electriques-1",
    "vehicules-a-faibles-et-a-tres-faibles-emissions-de-la-prefecture-de-region-auvergne-rhones-alpes",
    "base-adresse-nationale",
    "lignes-dautocars-urbains-et-interurbains-de-la-dlva",
    "nombre-de-personnes-rickrollees-sur-data-gouv-fr",
    ]
DATASET_SLUGS = []


DATASET_URL = '/api/1/datasets'
ORG_URL = '/api/1/organizations'
REUSE_URL = '/api/1/reuses'
COMMUNITY_RES_URL = '/api/1/datasets/community_resources'


DEFAULT_FIXTURE_FILE = ''  # noqa


@cli.command()
@click.argument('data-source')
def generate_fixtures_local_file(data_source):
    '''Build sample fixture file based on datasets slugs list (users, datasets, reuses).'''
    json_result = []

    with click.progressbar(DATASET_SLUGS) as bar:
        for slug in bar:
            json_fixture = {}

            json_dataset = requests.get(f'{data_source}{DATASET_URL}/{slug}/').json()
            del json_dataset['uri']
            del json_dataset['page']
            del json_dataset['last_update']
            del json_dataset['license']
            json_org = json_dataset.pop('organization')
            json_resources = json_dataset.pop('resources')
            for res in json_resources:
                del res['latest']
                del res['preview_url']
                del res['last_modified']
            json_fixture['resources'] = json_resources
            json_fixture['dataset'] = json_dataset

            json_org = requests.get(f"{data_source}{ORG_URL}/{json_org['id']}/").json()
            del json_org['members']
            del json_org['page']
            del json_org['uri']
            del json_org['logo_thumbnail']
            json_fixture['organization'] = json_org

            json_reuses = requests.get(f"{data_source}{REUSE_URL}/?dataset={json_dataset['id']}").json()['data']
            for reuse in json_reuses:
                del reuse['datasets']
                del reuse['image_thumbnail']
                del reuse['page']
                del reuse['uri']
                del reuse['organization']
                del reuse['owner']
            json_fixture['reuses'] = json_reuses

            json_community = requests.get(f"{data_source}{COMMUNITY_RES_URL}/?dataset={json_dataset['id']}").json()
            json_fixture['community_resources'] = json_community

            json_result.append(json_fixture)
    

    with open('results.json', 'w') as f:
        json.dump(json_result, f)


@cli.command()
@click.argument('source', default=DEFAULT_FIXTURE_FILE)
def generate_fixtures(source):
    '''Build sample fixture data (users, datasets, reuses) from local or remote file.'''
    if source.startswith('http'):
        json_fixtures = requests.get(source).json()
    else:
        with open(source) as f:
            json_fixtures = json.load(f)

    for fixture in json_fixtures:
        user = UserFactory()
        org = OrganizationFactory(**fixture['organization'], members=[Member(user=user)])
        dataset = DatasetFactory(**fixture['dataset'], organization=org)
        for resource in fixture['resources']:
            res = ResourceFactory(**resource)
            dataset.add_resource(res)
        for reuse in fixture['reuses']:
            ReuseFactory(**reuse, datasets=[dataset], owner=user)
