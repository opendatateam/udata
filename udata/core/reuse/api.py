# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI
from udata.forms import ReuseForm
from udata.models import Reuse

from udata.core.issues.api import IssuesAPI
from udata.core.followers.api import FollowAPI

from .api_fields import reuse_fields, reuse_page_fields
from .models import ReuseIssue, FollowReuse
from .search import ReuseSearch

ns = api.namespace('reuses', 'Reuse related operations')

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}
search_parser = api.search_parser(ReuseSearch)


@ns.route('/', endpoint='reuses')
@api.doc(
    get={'model': reuse_page_fields, 'parser': search_parser},
    post={'model': reuse_fields})
class ReuseListAPI(ModelListAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields
    search_adapter = ReuseSearch


@ns.route('/<reuse:reuse>/', endpoint='reuse', doc=common_doc)
@api.doc(model=reuse_fields)
class ReuseAPI(ModelAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields


@ns.route('/<reuse:reuse>/featured/', endpoint='reuse_featured')
@api.doc(**common_doc)
class ReuseFeaturedAPI(SingleObjectAPI, API):
    model = Reuse

    @api.secure
    @api.marshal_with(reuse_fields)
    def post(self, reuse):
        '''Mark a reuse as featured'''
        reuse.featured = True
        reuse.save()
        return reuse

    @api.secure
    @api.marshal_with(reuse_fields)
    def delete(self, reuse):
        '''Unmark a reuse as featured'''
        reuse.featured = False
        reuse.save()
        return reuse


@ns.route('/<id>/issues/', endpoint='reuse_issues')
class ReuseIssuesAPI(IssuesAPI):
    model = ReuseIssue


@ns.route('/<id>/follow/', endpoint='follow_reuse')
class FollowReuseAPI(FollowAPI):
    model = FollowReuse
