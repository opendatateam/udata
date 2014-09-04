# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from glob import iglob
from os.path import join, basename

import fiona

from fiona.crs import to_string
from shapely.geometry import shape, MultiPolygon
from shapely.ops import cascaded_union

from udata.commands import manager
from udata.models import Territory


EXTRACTORS = {}
AGGREGATORS = []


def territory_extractor(level, regex):
    def wrapper(func):
        compiled = re.compile(regex)
        EXTRACTORS[compiled] = (level, func)
        return func
    return wrapper


def register_aggregate(level, code, name, territories):
    AGGREGATORS.append((level, code, name, territories))


@territory_extractor('country', r'^TM_WORLD_BORDERS-')
def extract_country(polygon):
    '''
    Extract a country information from single MultiPolygon.
    Based on data from http://thematicmapping.org/downloads/world_borders.php
    '''
    props = polygon['properties']
    code = props['ISO2'].lower()
    name = 'Åland Islands' if code == 'ax' else props['NAME']  # Fix wrong character
    keys = {
        'iso2': code,
        'iso3': props['ISO3'].lower(),
        'un': props['UN'],
        'fips': (props.get('FIPS', '') or '').lower() or None,
    }
    # return code, name.decode('cp1252'), keys
    return code, name, keys


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

    print 'Imported {0} territories for level {1} from file {2}'.format(imported, level, filename)
    return imported


def build_aggregate(level, code, name, territories):
    print 'Building aggregate "{0}" (level={1}, code={2})'.format(name, level, code)
    polygons = []
    for tlevel, tcode in territories:
        try:
            territory = Territory.objects.get(level=tlevel, code=tcode)
        except Territory.DoesNotExist:
            print 'Territory {0}/{1} not found'.format(tlevel, tcode)
            continue
        if not shape(territory.geom).is_valid:
            print 'Skipping invalid polygon for {0}'.format(territory.name)
            continue
        if shape(territory.geom).is_empty:
            print 'Skipping empty polygon for {0}'.format(territory.name)
            continue
        polygons.append(territory.geom)

    geom = cascaded_union([shape(p) for p in polygons])
    if geom.geom_type == 'Polygon':
        geom = MultiPolygon([geom])
    try:
        territory = Territory.objects.get(level=level, code=code)
    except Territory.DoesNotExist:
        territory = Territory(level=level, code=code)
    territory.name = name
    territory.geom = geom.__geo_interface__
    territory.save()


@manager.command
def load_territories(folder, level=None):
    '''Load territories from a folder of zip files containing shapefiles'''
    total = 0

    for filename in iglob(join(folder, '*.zip')):
        for regex, (file_level, extractor) in EXTRACTORS.items():
            if level and file_level != level:
                continue
            if regex.match(basename(filename)):
                print 'Found matching file for level {0}: {1}'.format(file_level, basename(filename))
                total += extract_shapefile(filename, file_level, extractor)
                print '-' * 80

    if not level or level == 'aggregate':
        for level, code, name, territories in AGGREGATORS:
            build_aggregate(level, code, name, territories)
            total += 1
            print '-' * 80

        # Special world Aggregate
        build_aggregate('country-group', 'ww', 'World', [
            ('country', code) for code in Territory.objects(level='country').distinct('code')
        ])

    print 'Done: Imported {0} territories'.format(total)
