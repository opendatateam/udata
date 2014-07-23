# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI, marshal
from udata.forms import ReuseForm
from udata.models import Reuse
from udata.search import ReuseSearch

from udata.core.issues.api import IssuesAPI

from .models import ReuseIssue

reuse_fields = {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'uri': fields.SelfUrl('api.reuse', lambda o: {'slug': o.slug}),
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
    def post(self, slug):
        reuse = self.get_or_404(slug=slug)
        reuse.featured = True
        reuse.save()
        return marshal(reuse, reuse_fields)

    @api.secure
    def delete(self, slug):
        reuse = self.get_or_404(slug=slug)
        reuse.featured = False
        reuse.save()
        return marshal(reuse, reuse_fields)


class ReuseIssuesAPI(IssuesAPI):
    model = ReuseIssue

api.add_resource(ReuseListAPI, '/reuses/', endpoint=b'api.reuses')
api.add_resource(ReuseAPI, '/reuses/<string:slug>', endpoint=b'api.reuse')
api.add_resource(ReuseFeaturedAPI, '/reuses/<string:slug>/featured', endpoint=b'api.reuse_featured')
api.add_resource(ReuseIssuesAPI, '/reuses/<id>/issues/', endpoint=b'api.reuse_issues')
