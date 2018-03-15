# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import contextlib
import logging
import lzma
import tarfile
import shutil

from collections import Counter
from datetime import date
from string import Formatter
from urllib import urlretrieve

import click
import msgpack
import slugify

from bson import DBRef
from mongoengine import errors

from udata.commands import cli
from udata.core.dataset.models import Dataset
from udata.core.spatial.models import GeoLevel, GeoZone, SpatialCoverage
from udata.core.storages import logos, tmp

log = logging.getLogger(__name__)


def level_ref(level):
    return DBRef(GeoLevel._get_collection_name(), level)


@cli.group('spatial')
def grp():
    '''Geospatial related operations'''
    pass


@grp.command()
@click.argument('filename', metavar='<filename>')
@click.option('-d', '--drop', is_flag=True, help='Drop existing data')
def load(filename, drop=False):
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
        with tarfile.open(fileobj=xz) as f:
            f.extractall(tmp.root)

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
    counter = Counter()
    drom_zone = GeoZone.objects(id='country-subset:fr:drom').first()
    dromcom_zone = GeoZone.objects(id='country-subset:fr:dromcom').first()
    # Iter over datasets with zones
    for dataset in Dataset.objects(spatial__zones__gt=[]):
        counter['datasets'] += 1
        new_zones = []
        for zone in dataset.spatial.zones:
            if zone.id.startswith('fr/'):
                counter['zones'] += 1
                country, kind, zone_id = zone.id.split('/')
                zone_id = zone_id.upper()  # Corsica 2a/b case.
                if kind == 'town':
                    counter['towns'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:commune')
                        .valid_at(date.today())
                        .first())
                elif kind == 'county':
                    counter['counties'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:departement')
                        .valid_at(date.today())
                        .first())
                elif kind == 'region':
                    counter['regions'] += 1
                    # Only link to pre-2016 regions which kept the same id.
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:region')
                        .first())
                elif kind == 'epci':
                    counter['epcis'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:epci')
                        .valid_at(dataset.created_at.date())
                        .first())
                else:
                    new_zones.append(zone)
            elif zone.id.startswith('country-subset/fr'):
                counter['zones'] += 1
                subset, country, kind = zone.id.split('/')
                if kind == 'dom':
                    counter['drom'] += 1
                    new_zones.append(drom_zone)
                elif kind == 'domtom':
                    counter['dromcom'] += 1
                    new_zones.append(dromcom_zone)
            elif zone.id.startswith('country/'):
                counter['zones'] += 1
                counter['countries'] += 1
                new_zones.append(zone.id.replace('/', ':'))
            elif zone.id.startswith('country-group/'):
                counter['zones'] += 1
                counter['countrygroups'] += 1
                new_zones.append(zone.id.replace('/', ':'))
            else:
                new_zones.append(zone)
        dataset.update(
            spatial=SpatialCoverage(
                granularity=dataset.spatial.granularity,
                zones=[getattr(z, 'id', z) for z in new_zones if z]
            )
        )
    log.info(Formatter().vformat('''Summary
    Processed {zones} zones in {datasets} datasets:
    - {countrygroups} country groups (World/UE)
    - {countries} countries
    - France:
        - {regions} regions
        - {counties} counties
        - {epcis} EPCIs
        - {towns} towns
        - {drom} DROM
        - {dromcom} DROM-COM
    ''', (), counter))
    log.info('Done')
