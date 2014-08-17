# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI, marshal, pager
from udata.forms import ReuseForm
from udata.models import Reuse

from udata.core.organization.api import OrganizationField
from udata.core.dataset.api import DatasetField
from udata.core.issues.api import IssuesAPI
from udata.core.followers.api import FollowAPI

from .models import ReuseIssue, FollowReuse
from .search import ReuseSearch

ns = api.namespace('reuses', 'Reuse related operations')

reuse_fields = api.model('Reuse', {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'type': fields.String,
    'featured': fields.Boolean,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'deleted': fields.ISODateTime,
    'datasets': fields.List(DatasetField),
    'organization': OrganizationField,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.reuse', lambda o: {'reuse': o}),
})

reuse_page_fields = api.model('ReusePage', pager(reuse_fields))

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}


@ns.route('/', endpoint='reuses')
@api.doc(get={'model': reuse_page_fields}, post={'model': reuse_fields})
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
@api.doc(model=reuse_fields, **common_doc)
class ReuseFeaturedAPI(SingleObjectAPI, API):
    model = Reuse

    @api.secure
    def post(self, reuse):
        '''Mark a reuse as featured'''
        reuse.featured = True
        reuse.save()
        return marshal(reuse, reuse_fields)

    @api.secure
    def delete(self, reuse):
        '''Unmark a reuse as featured'''
        reuse.featured = False
        reuse.save()
        return marshal(reuse, reuse_fields)


@ns.route('/<id>/issues/', endpoint='reuse_issues')
class ReuseIssuesAPI(IssuesAPI):
    model = ReuseIssue


@ns.route('/<id>/follow/', endpoint='follow_reuse')
class FollowReuseAPI(FollowAPI):
    model = FollowReuse
