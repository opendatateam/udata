from bson import ObjectId

from flask import request, redirect, url_for, json

from udata.api import api, API, fields
from udata.auth import admin_permission
from udata.models import Dataset, Reuse
from udata.utils import multi_to_dict
from udata.rdf import (
    CONTEXT, RDF_EXTENSIONS,
    negociate_content, graph_response
)

from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.api_fields import reuse_fields

from .models import current_site
from .rdf import build_catalog

site_fields = api.model('Site', {
    'id': fields.String(
        description='The Site unique identifier', required=True),
    'title': fields.String(
        description='The site display title', required=True),
    'metrics': fields.Raw(attribute=lambda o: o.get_metrics(), description='The associated metrics', default={}),
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


@api.route('/site/data.<format>', endpoint='site_dataportal')
class SiteDataPortal(API):
    def get(self, format):
        '''Root RDF endpoint with content negociation handling'''
        url = url_for('api.site_rdf_catalog_format', format=format)
        return redirect(url)


@api.route('/site/catalog', endpoint='site_rdf_catalog')
class SiteRdfCatalog(API):
    def get(self):
        '''Root RDF endpoint with content negociation handling'''
        format = RDF_EXTENSIONS[negociate_content()]
        url = url_for('api.site_rdf_catalog_format', format=format)
        return redirect(url)


@api.route('/site/catalog.<format>', endpoint='site_rdf_catalog_format')
class SiteRdfCatalogFormat(API):
    def get(self, format):
        params = multi_to_dict(request.args)
        page = int(params.get('page', 1))
        page_size = int(params.get('page_size', 100))
        datasets = Dataset.objects.visible().paginate(page, page_size)
        catalog = build_catalog(current_site, datasets, format=format)
        return graph_response(catalog, format)


@api.route('/site/context.jsonld', endpoint='site_jsonld_context')
class SiteJsonLdContext(API):
    def get(self):
        return json.dumps(CONTEXT), 200, {'Content-Type': 'application/ld+json'}
