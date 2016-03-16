# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata.models import GeoZone


def check_for_town(query):
    if (not query
            or len(query) < 4
            or not current_app.config.get('ACTIVATE_TERRITORIES')):
        return False
    # If it's a code, try INSEE/postal, otherwise use the name.
    qs = GeoZone.objects(level='fr/town')
    if len(query) == 5 and query.isdigit():
        # First check INSEE code then the first postal code.
        try:
            return qs.get(code=query)
        except GeoZone.DoesNotExist:
            try:
                try:
                    return qs.get(keys__postal__contains=query)
                except GeoZone.MultipleObjectsReturned:
                    # Finally, we fall back on the most popular one.
                    # Warning: it means that we're dropping some territories
                    # here, e.g.: 62760 vs. 62814 vs. 80756.
                    geozones = qs(keys__postal__contains=query)
                    geozones = geozones.order_by('-population', '-area')
                    return geozones.first()
            except GeoZone.DoesNotExist:
                return False
    else:
        # First check on the start and fall back to exact
        # on multiple matches.
        try:
            return qs.get(name__istartswith=query)
        except GeoZone.MultipleObjectsReturned:
            try:
                return qs.get(name__iexact=query)
            except GeoZone.MultipleObjectsReturned:
                # Finally, we fall back on the most popular one.
                # Warning: it means that we're dropping some territories
                # here, e.g.: Vitrolles.
                geozones = qs(name__iexact=query)
                geozones = geozones.order_by('-population', '-area')
                return geozones.first()
            except GeoZone.DoesNotExist:
                return False
        except GeoZone.DoesNotExist:
            return False
