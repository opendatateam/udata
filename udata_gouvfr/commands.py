# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists

from udata.commands import manager
from udata.models import Organization
from udata.core.territories.commands import territory_extractor


@territory_extractor('district', r'^arrondissements-')
def extract_french_district(polygon):
    '''
    Extract a french district informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-arrondissements-francais-issus-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['insee_ar']
    name = props['nom']
    keys = {
        'insee': code,
    }
    return code, name, keys


@territory_extractor('epci', r'^epci-')
def extract_french_epci(polygon):
    '''
    Extract a french EPCI informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-epci-2014/
    '''
    props = polygon['properties']
    code = props['siren_epci']
    name = props.get('nom_osm') or props['nom_epci']
    keys = {
        'siren': props['siren_epci'],
        'ptot': props['ptot_epci'],
        'osm_id': props['osm_id'],
        'type_epci': props['type_epci']
    }
    return code, name.decode('cp1252'), keys


@territory_extractor('county', r'^departements-')
def extract_french_county(polygon):
    '''
    Extract a french country informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-departements-francais-issus-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['code_insee']
    name = props['nom']
    keys = {
        'insee': code,
        'nuts3': props['nuts3'],
    }
    return code, name.decode('cp1252'), keys


@territory_extractor('region', r'^regions-')
def extract_french_region(polygon):
    '''
    Extract a french region informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-regions-francaises-sur-openstreetmap/
    '''
    props = polygon['properties']
    code = props['code_insee']
    name = props['nom']
    keys = {
        'insee': code,
        'nuts2': props['nuts2'],
        'iso3166_2': props['iso3166_2'],
    }
    return code, name, keys


@territory_extractor('town', r'^communes-')
def extract_french_town(polygon):
    '''
    Extract a french town informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['insee']
    name = props['nom']
    keys = {
        'insee': code,
    }
    return code, name, keys


def certify_org(id_or_slug):
    organization = Organization.objects(slug=id_or_slug).first()
    if not organization:
        try:
            organization = Organization.objects(id=id_or_slug).first()
        except:
            print 'No organization found for {0}'.format(id_or_slug)
            return
    print 'Certifying {0}'.format(organization.name)
    organization.public_service = True
    organization.save()


@manager.command
def certify(path_or_id):
    '''Certify an organization as a public service'''
    if exists(path_or_id):
        with open(path_or_id) as open_file:
            for id_or_slug in open_file.readlines():
                certify_org(id_or_slug.strip())
    else:
        certify_org(path_or_id)
