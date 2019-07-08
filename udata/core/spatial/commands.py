# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import contextlib
import logging
import lzma
import tarfile
import shutil

from collections import Counter
from textwrap import dedent
from urllib import urlretrieve

import click
import msgpack
import slugify

from bson import DBRef
from mongoengine import errors

from udata.commands import cli
from udata.core.dataset.models import Dataset
from udata.core.spatial import geoids
from udata.core.spatial.models import GeoLevel, GeoZone, SpatialCoverage
from udata.core.storages import logos, tmp

log = logging.getLogger(__name__)


DEFAULT_GEOZONES_FILE = 'https://github.com/etalab/geozones/releases/download/2019.0/geozones-countries-2019-0-msgpack.tar.xz'


def level_ref(level):
    return DBRef(GeoLevel._get_collection_name(), level)


@cli.group('spatial')
def grp():
    '''Geospatial related operations'''
    pass


@grp.command()
@click.argument('filename', metavar='<filename>', default=DEFAULT_GEOZONES_FILE)
@click.option('-d', '--drop', is_flag=True, help='Drop existing data')
def load(filename=DEFAULT_GEOZONES_FILE, drop=False):
    '''
    Load a geozones archive from <filename>

    <filename> can be either a local path or a remote URL.
    '''
    if filename.startswith('http'):
        log.info('Downloading GeoZones bundle: %s', filename)
        filename, _ = urlretrieve(filename, tmp.path('geozones.tar.xz'))

    log.info('Extracting GeoZones bundle')
    with contextlib.closing(lzma.LZMAFile(filename)) as xz:
        with tarfile.open(fileobj=xz) as f:
            f.extractall(tmp.root)

    log.info('Loading GeoZones levels')

    if drop:
        log.info('Dropping existing levels')
        GeoLevel.drop_collection()

    log.info('Loading levels.msgpack')
    levels_filepath = tmp.path('levels.msgpack')
    with open(levels_filepath) as fp:
        unpacker = msgpack.Unpacker(fp, encoding=str('utf-8'))
        for i, level in enumerate(unpacker, start=1):
            GeoLevel.objects(id=level['id']).modify(
                upsert=True,
                set__name=level['label'],
                set__parents=[level_ref(p) for p in level['parents']],
                set__admin_level=level.get('admin_level')
            )
    os.remove(levels_filepath)
    log.info('Loaded {total} levels'.format(total=i))

    if drop:
        log.info('Dropping existing spatial zones')
        GeoZone.drop_collection()

    log.info('Loading zones.msgpack')
    zones_filepath = tmp.path('zones.msgpack')
    with open(zones_filepath) as fp:
        unpacker = msgpack.Unpacker(fp, encoding=str('utf-8'))
        unpacker.next()  # Skip headers.
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
                GeoZone.objects(id=geozone['_id']).modify(upsert=True, **{
                    'set__{0}'.format(k): v for k, v in params.items()
                })
            except errors.ValidationError as e:
                log.warning('Validation error (%s) for %s with %s',
                            e, geozone['_id'], params)
                continue
    os.remove(zones_filepath)
    log.info('Loaded {total} zones'.format(total=i))

    shutil.rmtree(tmp.path('translations'))  # Not in use for now.


def safe_tarinfo(tarinfo):
    '''make a tarinfo utf8-compatible'''
    tarinfo.name = tarinfo.name.decode('utf8')
    return tarinfo


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
            decoded = (safe_tarinfo(t) for t in tar.getmembers())
            tar.extractall(tmp.root, members=decoded)

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
