# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata import search, theme
from udata.frontend import front
from udata.models import Dataset, Organization, Reuse, User
from udata.utils import multi_to_dict
from udata.features.towns import check_for_town


@front.route('/search/', endpoint='search')
def render_search():
    params = multi_to_dict(request.args)
    params['facets'] = True
    # We only fetch relevant data for the given filter.
    if 'tag' in params:
        search_queries = [
            search.SearchQuery(Dataset, **params),
            search.SearchQuery(Reuse, **params)
        ]
        results_labels = ['datasets', 'reuses']
    elif 'badge' in params:
        search_queries = [
            search.SearchQuery(Dataset, **params),
            search.SearchQuery(Organization, **params)
        ]
        results_labels = ['datasets', 'organizations']
    else:
        search_queries = [
            search.SearchQuery(Dataset, **params),
            search.SearchQuery(Reuse, **params),
            search.SearchQuery(Organization, **params),
            search.SearchQuery(User, **params)
        ]
        results_labels = ['datasets', 'reuses', 'organizations', 'users']
    results = search.multiquery(*search_queries)
    context = dict(zip(results_labels, results))
    context['town'] = check_for_town(params.get('q'))
    return theme.render('search.html', **context)
