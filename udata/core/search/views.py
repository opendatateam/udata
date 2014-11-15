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
    datasets, organizations, reuses, users = search.multiquery(
        search.SearchQuery(Dataset, **params),
        search.SearchQuery(Organization, **params),
        search.SearchQuery(Reuse, **params),
        search.SearchQuery(User, **params),
    )
    return theme.render('search.html',
        datasets=datasets,
        organizations=organizations,
        reuses=reuses,
        users=users
    )
