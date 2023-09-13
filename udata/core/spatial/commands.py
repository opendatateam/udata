import json
import logging
import signal
import sys

from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from textwrap import dedent
import requests

import click
import slugify

from bson import DBRef
from mongoengine import errors
from mongoengine.context_managers import switch_collection

from udata.commands import cli
from udata.core.dataset.models import Dataset
from udata.core.spatial import geoids
from udata.core.spatial.models import GeoLevel, GeoZone, SpatialCoverage

log = logging.getLogger(__name__)


DEFAULT_GEOZONES_FILE = 'https://demo.data.gouv.fr/fr/datasets/r/7d5e912d-7567-43be-ab52-c18a165a070a'
DEFAULT_LEVELS_FILE = 'https://demo.data.gouv.fr/fr/datasets/r/5415fe00-20d5-4d50-8d04-4d2e9c39f07a'


@cli.group('spatial')
def grp():
    '''Geospatial related operations'''
    pass


def load_levels(col, json_levels):
    for i, level in enumerate(json_levels):
        col.objects(id=level['id']).modify(
            upsert=True,
            set__name=level['label'],
            set__admin_level=level.get('admin_level')
        )
    return i


def load_zones(col, json_geozones):
    for i, geozone in enumerate(json_geozones):
        params = {
            'slug': slugify.slugify(geozone['nom'], separator='-'),
            'level': str(geozone['level']),
            'code': geozone['codeINSEE'],
            'name': geozone['nom'],
            'uri': geozone['uri']
        }
        try:
            col.objects(id=geozone['_id']).modify(upsert=True, **{
                'set__{0}'.format(k): v for k, v in params.items()
            })
        except errors.ValidationError as e:
            log.warning('Validation error (%s) for %s with %s',
                        e, geozone['nom'], params)
            continue
    return i


@contextmanager
def handle_error(to_delete=None):
    '''
    Handle errors while loading.
    In case of error, properly log it, remove the temporary files and collections and exit.
    If `to_delete` is given a collection, it will be deleted deleted.
    '''
    # Handle keyboard interrupt
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    except KeyboardInterrupt:
        print('')  # Proper warning message under the "^C" display
        log.warning('Interrupted by signal')
    except Exception as e:
        log.error(e)
    else:
        return  # Nothing to do in case of success
    if to_delete:
        log.info('Removing temporary collection %s', to_delete._get_collection_name())
        to_delete.drop_collection()
    sys.exit(-1)


@grp.command()
@click.argument('geozones-file', default=DEFAULT_GEOZONES_FILE)
@click.argument('levels-file', default=DEFAULT_LEVELS_FILE)
@click.option('-d', '--drop', is_flag=True, help='Drop existing data')
def load(geozones_file, levels_file, drop=False):
    '''
    Load a geozones archive from <filename>

    <filename> can be either a local path or a remote URL.
    '''
    log.info('Loading GeoZones levels')
    if levels_file.startswith('http'):
        json_levels = requests.get(levels_file).json()['data']
    else:
        with open(levels_file) as f:
            json_levels = json.load(f)

    ts = datetime.utcnow().isoformat().replace('-', '').replace(':', '').split('.')[0]
    if drop and GeoLevel.objects.count():
        name = '_'.join((GeoLevel._get_collection_name(), ts))
        target = GeoLevel._get_collection_name()
        with switch_collection(GeoLevel, name):
            with handle_error(GeoLevel):
                total = load_levels(GeoLevel, json_levels)
                GeoLevel.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error():
            total = load_levels(GeoLevel, json_levels)
    log.info('Loaded {total} levels'.format(total=total))

    log.info('Loading Zones')
    if geozones_file.startswith('http'):
        json_geozones = requests.get(geozones_file).json()['data']
    else:
        with open(geozones_file) as f:
            json_geozones = json.load(f)

    if drop and GeoZone.objects.count():
        name = '_'.join((GeoZone._get_collection_name(), ts))
        target = GeoZone._get_collection_name()
        with switch_collection(GeoZone, name):
            with handle_error(GeoZone):
                total = load_zones(GeoZone, json_geozones)
                GeoZone.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error():
            total = load_zones(GeoZone, json_geozones)
    log.info('Loaded {total} zones'.format(total=total))


@grp.command()
def migrate():
    '''
    Migrate zones from old to new ids in datasets.

    Should only be run once with the new version of geozones w/ geohisto.
    '''
    counter = Counter(['zones', 'datasets'])
    qs = GeoZone.objects.only('id', 'level', 'successors')
    # Iter over datasets with zones
    for dataset in Dataset.objects(spatial__zones__gt=[]):
        counter['datasets'] += 1
        new_zones = []
        for current_zone in dataset.spatial.zones:
            counter['zones'] += 1
            level, code = geoids.parse(current_zone.id)
            zone = qs(level=level, code=code).first()
            if not zone:
                log.warning('No match for %s: skipped', current_zone.id)
                counter['skipped'] += 1
                continue
            new_zones.append(zone.id)
            counter[zone.level] += 1
        dataset.update(
            spatial=SpatialCoverage(
                granularity=dataset.spatial.granularity,
                zones=list(new_zones)
            )
        )
    level_summary = '\n'.join([
        ' - {0}: {1}'.format(l.id, counter[l.id])
        for l in GeoLevel.objects.order_by('admin_level')
    ])
    summary = '\n'.join([dedent('''\
    Summary
    =======
    Processed {zones} zones in {datasets} datasets:\
    '''.format(level_summary, **counter)), level_summary])
    log.info(summary)
    log.info('Done')
