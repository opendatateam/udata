# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import contextlib
import json
import logging
import lzma
import tarfile
import shutil
from urllib import urlretrieve

from udata.commands import submanager
from udata.core.storages import tmp
from udata.models import GeoLevel, GeoZone

log = logging.getLogger(__name__)


m = submanager(
    'spatial',
    help='Geospatial related operations',
    description='Handle all geospatial related operations and maintenance'
)


@m.command
def load(filename, drop=False):
    '''Load a GeoZones Bundle'''
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

    log.info('Loading levels.json')
    levels_filepath = tmp.path('levels.json')
    with open(levels_filepath) as fp:
        levels = json.load(fp)
    os.remove(levels_filepath)

    for level in levels:
        GeoLevel.objects.create(id=level['id'], name=level['label'],
                                parents=level['parents'])
    log.info('Loaded {total} levels'.format(total=len(levels)))

    if drop:
        log.info('Dropping existing spatial zones')
        GeoZone.drop_collection()

    log.info('Loading zones.json')
    zones_filepath = tmp.path('zones.json')
    with open(zones_filepath) as fp:
        geozones = json.load(fp)
    os.remove(zones_filepath)

    for zone in geozones['features']:
        props = zone['properties']
        GeoZone.objects.create(
            id=zone['id'],
            level=props['level'],
            code=props['code'],
            name=props['name'],
            keys=props['keys'],
            parents=props['parents'],
            population=props.get('population'),
            dbpedia=props.get('dbpedia'),
            logo=props.get('flag') or props.get('blazon'),
            wikipedia=props.get('wikipedia'),
            area=props.get('area'),
            geom=zone['geometry']
        )

    log.info('Loaded {total} zones'.format(total=len(geozones['features'])))
    shutil.rmtree(tmp.path('translations'))  # Not in use for now.
