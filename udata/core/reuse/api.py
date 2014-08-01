# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI, marshal
from udata.forms import ReuseForm
from udata.models import Reuse
from udata.search import ReuseSearch

from udata.core.organization.api import OrganizationField
from udata.core.dataset.api import DatasetField

from udata.core.issues.api import IssuesAPI

from .models import ReuseIssue

reuse_fields = {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'type': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'datasets': fields.List(DatasetField),
    'organization': OrganizationField,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.reuse', lambda o: {'reuse': o}),
}


class ReuseListAPI(ModelListAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields
    search_adapter = ReuseSearch


class ReuseAPI(ModelAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields


class ReuseFeaturedAPI(SingleObjectAPI, API):
    model = Reuse

    @api.secure
    def post(self, reuse):
        reuse.featured = True
        reuse.save()
        return marshal(reuse, reuse_fields)

    @api.secure
    def delete(self, reuse):
        reuse.featured = False
        reuse.save()
        return marshal(reuse, reuse_fields)


class ReuseIssuesAPI(IssuesAPI):
    model = ReuseIssue

api.add_resource(ReuseListAPI, '/reuses/', endpoint=b'api.reuses')
api.add_resource(ReuseAPI, '/reuses/<reuse:reuse>/', endpoint=b'api.reuse')
api.add_resource(ReuseFeaturedAPI, '/reuses/<reuse:reuse>/featured/', endpoint=b'api.reuse_featured')
api.add_resource(ReuseIssuesAPI, '/reuses/<id>/issues/', endpoint=b'api.reuse_issues')
