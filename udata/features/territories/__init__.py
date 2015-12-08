# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata.models import GeoZone


def check_for_territory(query):
    if (not query
            or len(query) < 4
            or not current_app.config.get('ACTIVATE_TERRITORIES')):
        return False
    # If it's a code, try INSEE/postal, otherwise use the name.
    if len(query) == 5 and query.isdigit():
        # First check INSEE code then postal code.
        try:
            return GeoZone.objects.get(code=query, level='fr/town')
        except GeoZone.DoesNotExist:
            try:
                return GeoZone.objects.get(
                    keys__postal__contains=query, level='fr/town')
            except GeoZone.DoesNotExist:
                return False
    else:
        # First check on the start and fall back to exact
        # on multiple matches.
        try:
            return GeoZone.objects.get(
                name__istartswith=query, level='fr/town')
        except GeoZone.MultipleObjectsReturned:
            try:
                return GeoZone.objects.get(name__iexact=query, level='fr/town')
            except GeoZone.MultipleObjectsReturned:
                # Finally, we fall back on the most popular one.
                # Warning: it means that we're dropping some territories
                # here, e.g.: Vitrolles.
                return (GeoZone.objects
                        .filter(name__iexact=query, level='fr/town')
                        .order_by('-population', '-area')
                        .first())
            except GeoZone.DoesNotExist:
                return False
        except GeoZone.DoesNotExist:
            return False
