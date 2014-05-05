# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata.frontend import front, render
from udata.search import DatasetSearch, OrganizationSearch, ReuseSearch, multisearch
from udata.utils import multi_to_dict


@front.route('/search')
def search():
    datasets, organizations, reuses = multisearch(
        DatasetSearch(**multi_to_dict(request.args)),
        OrganizationSearch(**multi_to_dict(request.args)),
        ReuseSearch(**multi_to_dict(request.args)),
    )
    return render('search.html',
        datasets=datasets,
        organizations=organizations,
        reuses=reuses,
    )
