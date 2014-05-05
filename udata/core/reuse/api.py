# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI, marshal
from udata.forms import ReuseForm
from udata.models import Reuse
from udata.search import ReuseSearch

reuse_fields = {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.DateTime
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

    def post(self, slug):
        reuse = self.get_or_404(slug=slug)
        reuse.featured = True
        reuse.save()
        return marshal(reuse, reuse_fields)

    def delete(self, slug):
        reuse = self.get_or_404(slug=slug)
        reuse.featured = False
        reuse.save()
        return marshal(reuse, reuse_fields)


api.add_resource(ReuseListAPI, '/reuses/', endpoint=b'api.reuses')
api.add_resource(ReuseAPI, '/reuses/<string:slug>', endpoint=b'api.reuse')
api.add_resource(ReuseFeaturedAPI, '/reuses/<string:slug>/featured', endpoint=b'api.reuse_featured')
