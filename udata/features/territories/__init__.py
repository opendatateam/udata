# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata.models import db, GeoZone


def check_for_territories(query):
    if (not query
            or len(query) < 4
            or not current_app.config.get('ACTIVATE_TERRITORIES')):
        return GeoZone.objects.none()
    # If it's a code, try INSEE/postal, otherwise use the name.
    qs = GeoZone.objects(level='fr/town')
    if len(query) == 5 and query.isdigit():
        # Match both INSEE and postal codes
        qs = qs(db.Q(code=query) | db.Q(keys__postal__contains=query))
    else:
        # Check names starting with query or exact match.
        qs = qs(db.Q(name__istartswith=query) | db.Q(name__iexact=query))
    # Sort matching result by pouplation and area
    return qs.order_by('-population', '-area')
