# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from shapely.geometry import MultiPolygon, shape
from shapely.ops import cascaded_union

from udata.tasks import celery
from udata.models import Dataset, GeoCoverage, Territory


LEVEL_MAPPING = {
    'regionoffrance': 'fr-region',
    'communeoffrance': 'fr-town',
    'country': 'country',
    'intercommunalityoffrance': 'fr-epci',
    'departmentoffrance': 'fr-county',
    'internationalorganization': 'country-group',
    'metropoleofcountry': 'country-subset',
    'overseascollectivityoffrance': 'fr-county',
    'overseasofcountry': 'country-subset',
}

SUBSETS = {
    'france d outre mer': 'fr-domtom',
    'france metropolitaine': 'fr-metro',
}


def territory_from_comarquage(co_code):
    parts = co_code.lower().split('/', 2)
    if len(parts) < 2:
        return None
    level = parts[0]
    # France metro & DOM-TOM
    if not level in LEVEL_MAPPING:
        print 'Unknown level "{0}" for "{1}"'.format(level, co_code)
        return None
    level = LEVEL_MAPPING[level]
    code = SUBSETS[parts[2]] if level == 'country-subset' else parts[1]
    try:
        return Territory.objects.get(level=level, code=code)
    except Territory.DoesNotExist:
        print 'Territory not found: level={0} code={1} for {2}'.format(level, code, co_code)
        return None


@celery.task
def geocode_territorial_coverage():
    for dataset in Dataset.objects(territorial_coverage__codes__not__size=0):
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
        coverage.granularity = dataset.territorial_coverage.granularity
        dataset.geo_coverage = coverage
        try:
            dataset.save()
        except Exception as e:
            print 'Unable to save dataset "{0}": {1}'.format(dataset.title, e)
