# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from shapely.geometry import MultiPolygon, shape
from shapely.ops import cascaded_union

from udata.tasks import celery
from udata.models import Dataset, SpatialCoverage, Territory


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

'''
MetropoleOfCountry/FR/FRANCE METROPOLITAINE
Country/FR/FRANCE
OverseasOfCountry/FR/FRANCE D OUTRE MER
RegionOfFrance/02/MARTINIQUE
CommuneOfFrance/44109/44000 NANTES
InternationalOrganization/UE/UNION EUROPEENNE
OverseasCollectivityOfFrance/975/975 ST PIERRE ET MIQUELON
IntercommunalityOfFrance/241300177/SAN OUEST PROVENCE
DepartmentOfFrance/60/60 OISE
'''

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


def territorial_to_spatial(territorial_coverage):
    '''Transform a datagouv v2 territorial coverage into a spatial coverage'''
    polygons = []
    coverage = SpatialCoverage()
    for code in territorial_coverage.codes:
        territory = territory_from_comarquage(code)
        if not territory:
            continue
        coverage.territories.append(territory.reference())
        polygons.append(territory.geom)
    polygon = cascaded_union([shape(p) for p in polygons])
    if polygon.is_empty:
        return None
    if polygon.geom_type == 'MultiPolygon':
        coverage.geom = polygon.__geo_interface__
    elif polygon.geom_type == 'Polygon':
        coverage.geom = MultiPolygon([polygon]).__geo_interface__
    else:
        raise ValueError('Unsupported geometry type "{0}"'.format(polygon.geom_type))
    coverage.granularity = territorial_coverage.granularity
    return coverage


@celery.task
def geocode_territorial_coverage():
    for dataset in Dataset.objects(extras__territorial_coverage__codes__not__size=0):
        if not 'territorial_coverage' in dataset.extras:
            continue
        try:
            dataset.spatial = territorial_to_spatial(dataset.extras['territorial_coverage'])
        except Exception as e:
            print 'Exception while processing {0}:'.format(dataset.title), e
            continue
        try:
            dataset.save()
        except Exception as e:
            print 'Unable to save dataset "{0}": {1}'.format(dataset.title, e)
