import os
import contextlib
import logging
import lzma
import tarfile
import shutil
import signal
import sys

from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from textwrap import dedent
from urllib.request import urlretrieve
import requests

import click
import msgpack
import slugify

from bson import DBRef
from mongoengine import errors
from mongoengine.context_managers import switch_collection

from udata.commands import cli
from udata.core.dataset.models import Dataset
from udata.core.spatial import geoids
from udata.core.spatial.models import GeoLevel, GeoZone, SpatialCoverage
from udata.core.storages import logos, tmp

log = logging.getLogger(__name__)


DEFAULT_GEOZONES_FILE = 'https://github.com/etalab/geozones/releases/download/2019.0/geozones-countries-2019-0-msgpack.tar.xz'
GEOZONE_FILENAME = 'geozones.tar.xz'


def level_ref(level):
    return DBRef(GeoLevel._get_collection_name(), level)


@cli.group('spatial')
def grp():
    '''Geospatial related operations'''
    pass


def load_levels(col, path):
    with open(path, 'rb') as fp:
        unpacker = msgpack.Unpacker(fp, raw=False)
        for i, level in enumerate(unpacker, start=1):
            col.objects(id=level['id']).modify(
                upsert=True,
                set__name=level['label'],
                set__parents=[level_ref(p) for p in level['parents']],
                set__admin_level=level.get('admin_level')
            )
    return i


def load_zones(col, path):
    with open(path, 'rb') as fp:
        unpacker = msgpack.Unpacker(fp, raw=False)
        next(unpacker)  # Skip headers.
        for i, geozone in enumerate(unpacker):
            params = {
                'slug': slugify.slugify(geozone['name'], separator='-'),
                'level': geozone['level'],
                'code': geozone['code'],
                'name': geozone['name'],
                'keys': geozone.get('keys'),
                'parents': geozone.get('parents', []),
                'ancestors': geozone.get('ancestors', []),
                'successors': geozone.get('successors', []),
                'validity': geozone.get('validity'),
                'population': geozone.get('population'),
                'dbpedia': geozone.get('dbpedia'),
                'flag': geozone.get('flag'),
                'blazon': geozone.get('blazon'),
                'wikidata': geozone.get('wikidata'),
                'wikipedia': geozone.get('wikipedia'),
                'area': geozone.get('area'),
            }
            if geozone.get('geom') and (
                geozone['geom']['type'] != 'GeometryCollection' or
                    geozone['geom']['geometries']):
                params['geom'] = geozone['geom']
            try:
                col.objects(id=geozone['_id']).modify(upsert=True, **{
                    'set__{0}'.format(k): v for k, v in params.items()
                })
            except errors.ValidationError as e:
                log.warning('Validation error (%s) for %s with %s',
                            e, geozone['_id'], params)
                continue
    return i


def cleanup(prefix):
    log.info('Removing temporary files')
    tmp.delete(prefix)
    if tmp.exists(GEOZONE_FILENAME):  # Has been downloaded
        tmp.delete(GEOZONE_FILENAME)


@contextmanager
def handle_error(prefix, to_delete=None):
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
    cleanup(prefix)
    if to_delete:
        log.info('Removing temporary collection %s', to_delete._get_collection_name())
        to_delete.drop_collection()
    sys.exit(-1)


@grp.command()
@click.argument('filename', metavar='<filename>', default=DEFAULT_GEOZONES_FILE)
@click.option('-d', '--drop', is_flag=True, help='Drop existing data')
def load(filename=DEFAULT_GEOZONES_FILE, drop=False):
    '''
    Load a geozones archive from <filename>

    <filename> can be either a local path or a remote URL.
    '''
    ts = datetime.now().isoformat().replace('-', '').replace(':', '').split('.')[0]
    prefix = 'geozones-{0}'.format(ts)
    if filename.startswith('http'):
        log.info('Downloading GeoZones bundle: %s', filename)
        # Use tmp.open to make sure that the directory exists in FS
        with tmp.open(GEOZONE_FILENAME, 'wb') as newfile:
            newfile.write(requests.get(filename).content)
            filename = tmp.path(GEOZONE_FILENAME)

    log.info('Extracting GeoZones bundle')
    with handle_error(prefix):
        with contextlib.closing(lzma.LZMAFile(filename)) as xz:
            with tarfile.open(fileobj=xz) as f:
                f.extractall(tmp.path(prefix))

    log.info('Loading GeoZones levels')

    log.info('Loading levels.msgpack')
    levels_filepath = tmp.path(prefix + '/levels.msgpack')
    if drop and GeoLevel.objects.count():
        name = '_'.join((GeoLevel._get_collection_name(), ts))
        target = GeoLevel._get_collection_name()
        with switch_collection(GeoLevel, name):
            with handle_error(prefix, GeoLevel):
                total = load_levels(GeoLevel, levels_filepath)
                GeoLevel.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error(prefix):
            total = load_levels(GeoLevel, levels_filepath)
    log.info('Loaded {total} levels'.format(total=total))

    log.info('Loading zones.msgpack')
    zones_filepath = tmp.path(prefix + '/zones.msgpack')
    if drop and GeoZone.objects.count():
        name = '_'.join((GeoZone._get_collection_name(), ts))
        target = GeoZone._get_collection_name()
        with switch_collection(GeoZone, name):
            with handle_error(prefix, GeoZone):
                total = load_zones(GeoZone, zones_filepath)
                GeoZone.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error(prefix):
            total = load_zones(GeoZone, zones_filepath)
    log.info('Loaded {total} zones'.format(total=total))

    cleanup(prefix)


@grp.command()
@click.argument('filename', metavar='<filename>')
def load_logos(filename):
    '''
    Load logos from a geologos archive from <filename>

    <filename> can be either a local path or a remote URL.
    '''
    if filename.startswith('http'):
        log.info('Downloading GeoLogos bundle: %s', filename)
        filename, _ = urlretrieve(filename, tmp.path('geologos.tar.xz'))

    log.info('Extracting GeoLogos bundle')
    with contextlib.closing(lzma.LZMAFile(filename)) as xz:
        with tarfile.open(fileobj=xz, encoding='utf8') as tar:
            tar.extractall(tmp.root, members=tar.getmembers())

    log.info('Moving to the final location and cleaning up')
    if os.path.exists(logos.root):
        shutil.rmtree(logos.root)
    shutil.move(tmp.path('logos'), logos.root)
    log.info('Done')


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
            level, code, validity = geoids.parse(current_zone.id)
            zone = qs(level=level, code=code).valid_at(validity).first()
            if not zone:
                log.warning('No match for %s: skipped', current_zone.id)
                counter['skipped'] += 1
                continue
            previous = None
            while not zone.is_current and len(zone.successors) == 1 and zone.id != previous:
                previous = zone.id
                zone = qs(id=zone.successors[0]).first() or zone
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
