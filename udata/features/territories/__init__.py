from flask import current_app

from udata.models import db, GeoZone


def check_for_territories(query):
    """
    Return a geozone queryset of territories given the `query`.

    Results are sorted by population and area (biggest first).
    """
    if not query or not current_app.config.get('ACTIVATE_TERRITORIES'):
        return []

    dbqs = db.Q()
    query = query.lower()
    is_digit = query.isdigit()
    query_length = len(query)
    for level in current_app.config.get('HANDLED_LEVELS'):
        if level == 'country':
            continue  # Level not fully handled yet.
        q = db.Q(level=level)
        if (query_length == 2 and level == 'fr:departement' and
                (is_digit or query in ('2a', '2b'))):
            # Counties + Corsica.
            q &= db.Q(code=query)
        elif query_length == 3 and level == 'fr:departement' and is_digit:
            # French DROM-COM.
            q &= db.Q(code=query)
        elif query_length == 5 and level == 'fr:commune' and (
                is_digit or query.startswith('2a') or query.startswith('2b')):
            # INSEE code then postal codes with Corsica exceptions.
            q &= db.Q(code=query) | db.Q(keys__postal__contains=query)
        elif query_length >= 4:
            # Check names starting with query or exact match.
            q &= db.Q(name__istartswith=query) | db.Q(name__iexact=query)
        else:
            continue

        # Meta Q object, ready to be passed to a queryset.
        dbqs |= q

    if dbqs.empty:
        return []

    # Sort matching results by population and area.
    return GeoZone.objects(dbqs).order_by('-population', '-area')
