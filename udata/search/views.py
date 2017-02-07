# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata import search, theme
from udata.frontend import front
from udata.models import Dataset, Organization, Reuse
from udata.utils import multi_to_dict
from udata.features.territories import check_for_territories

# Maps template variables names to model types
MAPPING = {
    'datasets': Dataset,
    'reuses': Reuse,
    'organizations': Organization,
}


@front.route('/search/', endpoint='search')
def render_search():
    params = multi_to_dict(request.args)
    params['facets'] = True
    # We only fetch relevant data for the given filter.
    if 'tag' in params:
        types = ['datasets', 'reuses']
    elif 'badge' in params:
        types = ['datasets', 'organizations']
    else:
        types = ['datasets', 'reuses', 'organizations']
    models = [MAPPING[typ] for typ in types]
    results = search.multisearch(*models, **params)
    context = dict(zip(types, results))
    territories = check_for_territories(params.get('q'))
    context['territories'] = territories
    return theme.render('search.html', **context)
