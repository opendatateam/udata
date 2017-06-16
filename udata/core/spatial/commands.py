# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import contextlib
import logging
import lzma
import tarfile
import shutil
from urllib import urlretrieve

import msgpack
import slugify
from mongoengine import errors

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

    log.info('Loading levels.msgpack')
    levels_filepath = tmp.path('levels.msgpack')
    with open(levels_filepath) as fp:
        unpacker = msgpack.Unpacker(fp, encoding=str('utf-8'))
        for i, level in enumerate(unpacker, start=1):
            GeoLevel.objects.create(
                id=level['id'],
                name=level['label'],
                parents=level['parents'],
                admin_level=level.get('admin_level')
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
            if not geozone.get('geom') or (
                geozone['geom']['type'] == 'GeometryCollection' and
                    not geozone['geom']['geometries']):
                geom = None
            else:
                geom = geozone['geom']
            params = {
                'id': geozone['_id'],
                'slug': slugify.slugify(geozone['name'], separator='-'),
                'level': geozone['level'],
                'code': geozone['code'],
                'name': geozone['name'],
                'keys': geozone.get('keys'),
                'parents': geozone.get('parents'),
                'ancestors': geozone.get('ancestors'),
                'successors': geozone.get('successors'),
                'validity': geozone.get('validity'),
                'population': geozone.get('population'),
                'dbpedia': geozone.get('dbpedia'),
                'flag': geozone.get('flag'),
                'blazon': geozone.get('blazon'),
                'wikipedia': geozone.get('wikipedia'),
                'area': geozone.get('area'),
                'geom': geom
            }
            try:
                GeoZone.objects.create(**params)
            except errors.ValidationError as e:
                log.warning('Validation error (%s) for %s with %s',
                            e, geozone, params)
                continue
    os.remove(zones_filepath)
    log.info('Loaded {total} zones'.format(total=i))

    shutil.rmtree(tmp.path('translations'))  # Not in use for now.
