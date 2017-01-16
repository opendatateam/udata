# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId

from flask import request

from udata.api import api, API, fields
from udata.auth import admin_permission
from udata.models import Dataset, Reuse

from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.api_fields import reuse_fields

from .views import current_site

site_fields = api.model('Site', {
    'id': fields.String(
        description='The Site unique identifier', required=True),
    'title': fields.String(
        description='The site display title', required=True),
    'metrics': fields.Raw(description='The associated metrics', default={}),
})


@api.route('/site/', endpoint='site')
class SiteAPI(API):

    @api.doc(id='get_site')
    @api.marshal_with(site_fields)
    def get(self):
        '''Site-wide variables'''
        return current_site


@api.route('/site/home/datasets/', endpoint='home_datasets')
class SiteHomeDatasetsAPI(API):
    @api.doc('get_home_datasets')
    # @api.secure(admin_permission)
    @api.marshal_list_with(dataset_fields)
    def get(self):
        '''List homepage datasets'''
        return current_site.settings.home_datasets

    @api.secure(admin_permission)
    @api.doc('set_home_datasets')
    @api.expect(([str], 'Dataset IDs to put in homepage'))
    @api.marshal_list_with(dataset_fields)
    def put(self):
        '''Set the homepage datasets editorial selection'''
        if not isinstance(request.json, list):
            api.abort(400, 'Expect a list of dataset IDs')
        ids = [ObjectId(id) for id in request.json]
        current_site.settings.home_datasets = Dataset.objects.bulk_list(ids)
        current_site.save()
        return current_site.settings.home_datasets


@api.route('/site/home/reuses/', endpoint='home_reuses')
class SiteHomeReusesAPI(API):
    @api.doc('get_home_reuses')
    @api.secure(admin_permission)
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List homepage featured reuses'''
        return current_site.settings.home_reuses

    @api.secure(admin_permission)
    @api.doc('set_home_reuses')
    @api.expect(([str], 'Reuse IDs to put in homepage'))
    @api.marshal_list_with(reuse_fields)
    def put(self):
        '''Set the homepage reuses editorial selection'''
        if not isinstance(request.json, list):
            api.abort(400, 'Expect a list of reuse IDs')
        ids = [ObjectId(id) for id in request.json]
        current_site.settings.home_reuses = Reuse.objects.bulk_list(ids)
        current_site.save()
        return current_site.settings.home_reuses
