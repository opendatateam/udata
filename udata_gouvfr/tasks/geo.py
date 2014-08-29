# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from shapely.geometry import MultiPolygon, shape
from shapely.ops import cascaded_union

from udata.tasks import celery
from udata.models import Dataset, GeoCoverage, Territory


LEVEL_MAPPING = {
    'RegionOfFrance': 'region',
    'CommuneOfFrance': 'town',
    'Country': 'country',
    'IntercommunalityOfFrance': 'epci',
    'DepartmentOfFrance': 'county',
}


def territory_from_comarquage(code):
    parts = code.split('/', 2)
    if len(parts) < 2:
        return None
    level, code = parts[0], parts[1].lower()
    # level, code, tail = code.split('/', 2)
    if not level in LEVEL_MAPPING:
        print 'Unknown level "{0}"'.format(level)
        return None
    level = LEVEL_MAPPING[level]
    try:
        return Territory.objects.get(level=level, code=code)
    except Territory.DoesNotExist:
        print 'Territory not found: level={0} code={1}'.format(level, code)
        return None




@celery.task
def geocode_territorial_coverage():
    for dataset in Dataset.objects:
        if not dataset.territorial_coverage:
            continue
        polygons = []
        coverage = GeoCoverage()
        for code in dataset.territorial_coverage.codes:
            territory = territory_from_comarquage(code)
            if not territory:
                continue
            coverage.territories.append(territory.reference())
            polygons.append(territory.geom)
        polygon = cascaded_union([shape(p) for p in polygons])
        if polygon.is_empty:
            continue
        if polygon.geom_type == 'MultiPolygon':
            coverage.geom = polygon.__geo_interface__
        elif polygon.geom_type == 'Polygon':
            coverage.geom = MultiPolygon([polygon]).__geo_interface__
        else:
            print 'Unsupported geometry type "{0}" for "{1}"'.format(polygon.geom_type, dataset.name)
            continue
        dataset.geo_coverage = coverage
        try:
            dataset.save()
        except:
            print 'Unable to save dataset "{0}"'.format(dataset.title)
