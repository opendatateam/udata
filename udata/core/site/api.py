from bson import ObjectId
from flask import json, make_response, redirect, request, url_for
from mongoengine import Q

from udata.api import API, api, fields
from udata.auth import admin_permission
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.api_fields import reuse_fields
from udata.models import Dataset, Reuse
from udata.rdf import CONTEXT, RDF_EXTENSIONS, graph_response, negociate_content
from udata.utils import multi_to_dict

from .models import current_site
from .rdf import build_catalog

site_fields = api.model(
    "Site",
    {
        "id": fields.String(description="The Site unique identifier", required=True),
        "title": fields.String(description="The site display title", required=True),
        "metrics": fields.Raw(
            attribute=lambda o: o.get_metrics(), description="The associated metrics", default={}
        ),
    },
)


@api.route("/site/", endpoint="site")
class SiteAPI(API):
    @api.doc(id="get_site")
    @api.marshal_with(site_fields)
    def get(self):
        """Site-wide variables"""
        return current_site


@api.route("/site/home/datasets/", endpoint="home_datasets")
class SiteHomeDatasetsAPI(API):
    @api.doc("get_home_datasets")
    # @api.secure(admin_permission)
    @api.marshal_list_with(dataset_fields)
    def get(self):
        """List homepage datasets"""
        return current_site.settings.home_datasets

    @api.secure(admin_permission)
    @api.doc("set_home_datasets")
    @api.expect(([str], "Dataset IDs to put in homepage"))
    @api.marshal_list_with(dataset_fields)
    def put(self):
        """Set the homepage datasets editorial selection"""
        if not isinstance(request.json, list):
            api.abort(400, "Expect a list of dataset IDs")
        ids = [ObjectId(id) for id in request.json]
        current_site.settings.home_datasets = Dataset.objects.bulk_list(ids)
        current_site.save()
        return current_site.settings.home_datasets


@api.route("/site/home/reuses/", endpoint="home_reuses")
class SiteHomeReusesAPI(API):
    @api.doc("get_home_reuses")
    @api.secure(admin_permission)
    @api.marshal_list_with(reuse_fields)
    def get(self):
        """List homepage featured reuses"""
        return current_site.settings.home_reuses

    @api.secure(admin_permission)
    @api.doc("set_home_reuses")
    @api.expect(([str], "Reuse IDs to put in homepage"))
    @api.marshal_list_with(reuse_fields)
    def put(self):
        """Set the homepage reuses editorial selection"""
        if not isinstance(request.json, list):
            api.abort(400, "Expect a list of reuse IDs")
        ids = [ObjectId(id) for id in request.json]
        current_site.settings.home_reuses = Reuse.objects.bulk_list(ids)
        current_site.save()
        return current_site.settings.home_reuses


@api.route("/site/data.<format>", endpoint="site_dataportal")
class SiteDataPortal(API):
    def get(self, format):
        """Root RDF endpoint with content negociation handling"""
        url = url_for("api.site_rdf_catalog_format", format=format)
        return redirect(url)


@api.route("/site/catalog", endpoint="site_rdf_catalog")
class SiteRdfCatalog(API):
    def get(self):
        """Root RDF endpoint with content negociation handling"""
        format = RDF_EXTENSIONS[negociate_content()]
        url = url_for("api.site_rdf_catalog_format", format=format)
        return redirect(url)


@api.route("/site/catalog.<format>", endpoint="site_rdf_catalog_format")
class SiteRdfCatalogFormat(API):
    def get(self, format):
        params = multi_to_dict(request.args)
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 100))
        datasets = Dataset.objects.visible()
        if "tag" in params:
            datasets = datasets.filter(tags=params.get("tag", ""))
        datasets = datasets.paginate(page, page_size)

        # We need to add Dataservice to the catalog.
        # In the best world, we want:
        # - Keep the correct number of datasets on the page (if the requested page size is 100, we should have 100 datasets)
        # - Have simple MongoDB queries
        # - Do not duplicate the datasets (each dataset is present once in the catalog)
        # - Do not duplicate the dataservices (each dataservice is present once in the catalog)
        # - Every referenced dataset for one dataservices present on the page (hard to do)
        #
        # Multiple solutions are possible but none check all the constraints.
        # The selected one is to put all the dataservices referencing at least one of the dataset on
        # the page at the end of it. It means dataservices could be duplicated (present on multiple pages)
        # and these dataservices may referenced some datasets not present in the current page. It's working
        # if somebody is doing the same thing as us (keeping the list of all the datasets IDs for the entire catalog then
        # listing all dataservices in a second pass)
        # Another option is to do some tricky Mongo requests to order/group datasets by their presence in some dataservices but
        # it could be really hard to do with a n..n relation.
        # Let's keep this solution simple right now and iterate on it in the future.
        dataservices_filter = Q(datasets__in=[d.id for d in datasets])

        # On the first page, add all dataservices without datasets
        if page == 1:
            dataservices_filter = dataservices_filter | Q(datasets__size=0)

        dataservices = Dataservice.objects.visible().filter(dataservices_filter)

        catalog = build_catalog(current_site, datasets, dataservices=dataservices, format=format)
        # bypass flask-restplus make_response, since graph_response
        # is handling the content negociation directly
        return make_response(*graph_response(catalog, format))


@api.route("/site/context.jsonld", endpoint="site_jsonld_context")
class SiteJsonLdContext(API):
    def get(self):
        response = make_response(json.dumps(CONTEXT))
        response.headers["Content-Type"] = "application/ld+json"
        return response
