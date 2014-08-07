# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata import search
from udata.frontend import front, render
from udata.models import Dataset, Organization, Reuse
from udata.utils import multi_to_dict


@front.route('/search/', endpoint='search')
def render_search():
    params = multi_to_dict(request.args)
    params['facets'] = True
    datasets, organizations, reuses = search.multiquery(
        search.SearchQuery(Dataset, **params),
        search.SearchQuery(Organization, **params),
        search.SearchQuery(Reuse, **params),
    )
    return render('search.html',
        datasets=datasets,
        organizations=organizations,
        reuses=reuses,
    )
