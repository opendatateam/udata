# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata import search, theme
from udata.frontend import front
from udata.models import Dataset, Organization, Reuse, User
from udata.utils import multi_to_dict


@front.route('/search/', endpoint='search')
def render_search():
    params = multi_to_dict(request.args)
    params['facets'] = True
    search_queries = [
        search.SearchQuery(Dataset, **params),
        search.SearchQuery(Reuse, **params)
    ]
    results_labels = ['datasets', 'reuses']
    # We only fetch orgs and users if this is not a tag-based search
    # because these resources do not have tags so it's irrelevant.
    if 'tag' not in params:
        search_queries += [
            search.SearchQuery(Organization, **params),
            search.SearchQuery(User, **params)
        ]
        results_labels += ['organizations', 'users']
    results = search.multiquery(*search_queries)
    return theme.render('search.html',
                        **dict(zip(results_labels, results)))
