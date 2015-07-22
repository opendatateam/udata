# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import json
import logging
import lzma
import tempfile
import tarfile
import shutil

from os.path import join
from urllib import urlretrieve

from udata.commands import submanager
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
    tmp = tempfile.mkdtemp()

    if filename.startswith('http'):
        log.info('Downloading GeoZones bundle: %s', filename)
        filename, _ = urlretrieve(filename, join(tmp, 'geozones.tar.xz'))

    log.info('Extracting GeoZones bundle')
    with contextlib.closing(lzma.LZMAFile(filename)) as xz:
        with tarfile.open(fileobj=xz) as f:
            f.extractall(tmp)

    log.info('Loading GeoZones levels')

    if (drop):
        log.info('Dropping existing levels')
        GeoLevel.drop_collection()

    log.info('Loading levels.json')
    total = 0
    with open(join(tmp, 'levels.json')) as fp:
        levels = json.load(fp)

    for level in levels:
        GeoLevel.objects.create(id=level['id'], name=level['label'],
                                parents=level['parents'])
        total += 1
    log.info('Loaded {0} levels'.format(total))

    if (drop):
        log.info('Dropping existing spatial zones')
        GeoZone.drop_collection()

    log.info('Loading zones.json')
    total = 0
    with open(join(tmp, 'zones.json')) as fp:
        geozones = json.load(fp)

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
            area=props.get('area'),
            geom=zone['geometry']
        )
        total += 1

    log.info('Loaded {0} zones'.format(total))

    log.info('Cleaning temporary working directory')
    shutil.rmtree(tmp)
