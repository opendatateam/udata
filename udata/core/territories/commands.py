# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from glob import iglob
from os.path import join, basename

import fiona

from fiona.crs import to_string
from shapely.geometry import shape, MultiPolygon

from udata.commands import manager
from udata.core.territories.models import Territory


EXTRACTORS = {}


def territory_extractor(level, regex):
    def wrapper(func):
        compiled = re.compile(regex)
        EXTRACTORS[compiled] = (level, func)
        return func
    return wrapper


@territory_extractor('country', r'^TM_WORLD_BORDER-')
def extract_country(polygon):
    '''
    Extract a country information from single MultiPolygon.
    Based on data from http://thematicmapping.org/downloads/world_borders.php
    '''
    props = polygon['properties']
    code = props['ISO2'].lower()
    name = props['NAME']
    keys = {
        'iso2': code,
        'iso3': props['ISO3'].lower(),
        'un': props['UN'].lower(),
        'fips': props['FIPS'].lower(),
    }
    return code, name.decode('cp1252'), keys


def extract_shapefile(filename, level, extractor):
    '''Extract territories from a given file for a given level with a given extractor function'''
    imported = 0

    with fiona.open('/', vfs='zip://{0}'.format(filename), encoding='utf8') as collection:
        print 'Extracting {0} elements from {1} ({2} {3})'.format(
            len(collection), basename(filename), collection.driver, to_string(collection.crs)
        )

        for polygon in collection:
            try:
                code, name, keys = extractor(polygon)
                geom = shape(polygon['geometry'])
                if geom.geom_type == 'Polygon':
                    geom = MultiPolygon([geom])
                elif geom.geom_type != 'MultiPolygon':
                    print 'Unsupported geometry type "{0}" for "{1}"'.format(geom.geom_type, name)
                    continue
                territory, _ = Territory.objects.get_or_create(level=level, code=code, defaults={
                    'geom': geom.__geo_interface__,
                    'name': name,
                    'keys': keys,
                })
                territory.geom = geom.__geo_interface__
                territory.name = name
                territory.keys = keys
                territory.save()
                imported += 1
            except Exception as e:
                print 'Error extracting polygon {0}: {1}'.format(polygon['properties'], e)
                print code, name

    print 'Imported {0} territories for level {1} from file {2}'.format(imported, level, filename)
    return imported


@manager.command
def load_territories(folder, level=None):
    '''Load territories from a folder of zip files containing shapefiles'''
    total = 0

    for filename in iglob(join(folder, '*.zip')):
        for regex, (file_level, extractor) in EXTRACTORS.items():
            if level and file_level != level:
                continue
            if regex.match(basename(filename)):
                print '-' * 80
                print 'Found matching file for level {0}: {1}'.format(file_level, basename(filename))
                total += extract_shapefile(filename, file_level, extractor)
                print '-' * 80

    print 'Done: Imported {0} territories'.format(total)
