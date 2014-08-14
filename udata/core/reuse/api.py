# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI, marshal
from udata.forms import ReuseForm
from udata.models import Reuse

from udata.core.organization.api import OrganizationField
from udata.core.dataset.api import DatasetField

from udata.core.issues.api import IssuesAPI

from .models import ReuseIssue
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


@ns.route('/', endpoint='reuses')
class ReuseListAPI(ModelListAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields
    search_adapter = ReuseSearch


@ns.route('/<reuse:reuse>/', endpoint='reuse')
class ReuseAPI(ModelAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields


@ns.route('/<reuse:reuse>/featured/', endpoint='reuse_featured')
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
