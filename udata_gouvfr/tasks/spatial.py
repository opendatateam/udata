# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from shapely.geometry import MultiPolygon, shape
from shapely.ops import cascaded_union

from udata.tasks import celery
from udata.models import Dataset, SpatialCoverage, Territory

log = logging.getLogger(__name__)


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
        log.error('Unknown level "%s" for "%s"', level, co_code)
        return None
    level = LEVEL_MAPPING[level]
    code = SUBSETS[parts[2]] if level == 'country-subset' else parts[1]
    try:
        return Territory.objects.get(level=level, code=code)
    except Territory.DoesNotExist:
        log.error('Territory not found: level=%s code=%s for %s', level, code, co_code)
        return None


def territorial_to_spatial(dataset):
    '''Transform a datagouv v2 territorial coverage into a spatial coverage'''
    if 'territorial_coverage' not in dataset.extras:
        return None
    territorial_coverage = dataset.extras['territorial_coverage']
    polygons = []
    coverage = SpatialCoverage()
    coverage.granularity = territorial_coverage.granularity
    for code in territorial_coverage.codes:
        territory = territory_from_comarquage(code)
        if not territory:
            continue
        coverage.territories.append(territory.reference())
        polygons.append(territory.geom)
    polygon = cascaded_union([shape(p) for p in polygons])
    if polygon.is_empty:
        log.error('Empty polygon for dataset "%s"', dataset.title)
    elif polygon.geom_type == 'MultiPolygon':
        coverage.geom = polygon.__geo_interface__
    elif polygon.geom_type == 'Polygon':
        coverage.geom = MultiPolygon([polygon]).__geo_interface__
    else:
        log.error('Unsupported geometry type "%s" for dataset "%s"', polygon.geom_type, dataset.title)
    return coverage


@celery.task
def geocode_territorial_coverage():
    for dataset in Dataset.objects(extras__territorial_coverage__codes__not__size=0):
        if not 'territorial_coverage' in dataset.extras:
            continue
        try:
            dataset.spatial = territorial_to_spatial(dataset)
        except:
            log.exception('Exception while processing dataset %s:', dataset.title)
            continue
        try:
            dataset.save()
        except:
            log.exception('Unable to save dataset "%s"', dataset.title)
