# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata.models import db, GeoZone


def check_for_towns(query):
    """
    Return a geozone queryset of towns given the `query`.

    If it's a code, try INSEE/postal, otherwise use the name.
    """
    if (not query or len(query) < 4 or
            not current_app.config.get('ACTIVATE_TERRITORIES')):
        return GeoZone.objects.none()
    qs = GeoZone.objects(level='fr/town')
    if len(query) == 5 and query.isdigit():
        # Match both INSEE and postal codes.
        qs = qs(db.Q(code=query) | db.Q(keys__postal__contains=query))
    else:
        # Check names starting with query or exact match.
        qs = qs(db.Q(name__istartswith=query) | db.Q(name__iexact=query))
    # Sort matching results by population and area.
    return qs.order_by('-population', '-area')


def check_for_counties(query):
    """
    Return a geozone queryset of counties given the `query`.

    If it's a 2/3-digits code try it, otherwise use the name.
    """
    if (not query or len(query) < 2 or
            not current_app.config.get('ACTIVATE_TERRITORIES')):
        return GeoZone.objects.none()
    qs = GeoZone.objects(level='fr/county')
    if ((len(query) == 2
            and (query.isdigit() or query.lower() in ('2a', '2b')))
            or len(query) == 3 and query.isdigit()):
        # Check county by code, including Corsica and DROM-COM.
        qs = qs(db.Q(code__iexact=query))
    else:
        # Check names starting with query or exact match.
        qs = qs(db.Q(name__istartswith=query) | db.Q(name__iexact=query))
    # Sort matching results by population and area.
    return qs.order_by('-population', '-area')


def check_for_regions(query):
    """
    Return a geozone queryset of regions given the `query`.
    """
    if (not query or len(query) < 4 or
            not current_app.config.get('ACTIVATE_TERRITORIES')):
        return GeoZone.objects.none()
    qs = GeoZone.objects(level='fr/region')
    # Check names starting with query or exact match.
    qs = qs(db.Q(name__istartswith=query) | db.Q(name__iexact=query))
    # Sort matching results by population and area.
    return qs.order_by('-population', '-area')
