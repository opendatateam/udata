from bson import ObjectId
from flask import current_app, json, make_response, redirect, request, url_for

from udata.api import API, api, fields
from udata.auth import admin_permission
from udata.core import csv
from udata.core.dataservices.csv import DataserviceCsvAdapter
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api import DatasetApiParser
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.csv import ResourcesCsvAdapter
from udata.core.dataset.search import DatasetSearch
from udata.core.dataset.tasks import get_queryset as get_csv_queryset
from udata.core.organization.api import OrgApiParser
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.organization.models import Organization
from udata.core.reuse.api import ReuseApiParser
from udata.core.reuse.csv import ReuseCsvAdapter
from udata.harvest.csv import HarvestSourceCsvAdapter
from udata.harvest.models import HarvestSource
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
    @api.marshal_list_with(Reuse.__read_fields__)
    def get(self):
        """List homepage featured reuses"""
        return current_site.settings.home_reuses

    @api.secure(admin_permission)
    @api.doc("set_home_reuses")
    @api.expect(([str], "Reuse IDs to put in homepage"))
    @api.marshal_list_with(Reuse.__read_fields__)
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
        dataservices = Dataservice.objects.visible().filter_by_dataset_pagination(datasets, page)

        catalog = build_catalog(current_site, datasets, dataservices=dataservices, format=format)
        # bypass flask-restplus make_response, since graph_response
        # is handling the content negociation directly
        return make_response(*graph_response(catalog, format))


@api.route("/site/datasets.csv", endpoint="site_datasets_csv")
class SiteDatasetsCsv(API):
    def get(self):
        # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if not request.args and "dataset" in exported_models:
            return redirect(get_export_url("dataset"))
        search_parser = DatasetSearch.as_request_parser(store_missing=False)
        params = search_parser.parse_args()
        params["facets"] = False
        datasets = DatasetApiParser.parse_filters(get_csv_queryset(Dataset), params)
        adapter = csv.get_adapter(Dataset)
        return csv.stream(adapter(datasets), "datasets")


@api.route("/site/resources.csv", endpoint="site_datasets_resources_csv")
class SiteResourcesCsv(API):
    def get(self):
        # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if not request.args and "resource" in exported_models:
            return redirect(get_export_url("resource"))
        search_parser = DatasetSearch.as_request_parser(store_missing=False)
        params = search_parser.parse_args()
        params["facets"] = False
        datasets = DatasetApiParser.parse_filters(get_csv_queryset(Dataset), params)
        return csv.stream(ResourcesCsvAdapter(datasets), "resources")


@api.route("/site/organizations.csv", endpoint="site_organizations_csv")
class SiteOrganizationsCsv(API):
    def get(self):
        params = multi_to_dict(request.args)
        # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if not params and "organization" in exported_models:
            return redirect(get_export_url("organization"))
        params["facets"] = False
        organizations = OrgApiParser.parse_filters(get_csv_queryset(Organization), params)
        return csv.stream(OrganizationCsvAdapter(organizations), "organizations")


@api.route("/site/reuses.csv", endpoint="site_reuses_csv")
class SiteReusesCsv(API):
    def get(self):
        params = multi_to_dict(request.args)
        # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if not params and "reuse" in exported_models:
            return redirect(get_export_url("reuse"))
        params["facets"] = False
        reuses = ReuseApiParser.parse_filters(get_csv_queryset(Reuse), params)
        return csv.stream(ReuseCsvAdapter(reuses), "reuses")


@api.route("/site/dataservices.csv", endpoint="site_dataservices_csv")
class SiteDataservicesCsv(API):
    def get(self):
        params = multi_to_dict(request.args)
        # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if not params and "dataservice" in exported_models:
            return redirect(get_export_url("dataservice"))
        params["facets"] = False
        dataservices = Dataservice.apply_sort_filters(get_csv_queryset(Dataservice))
        return csv.stream(DataserviceCsvAdapter(dataservices), "dataservices")


@api.route("/site/harvests.csv", endpoint="site_harvests_csv")
class SiteHarvestsCsv(API):
    def get(self):
        # redirect to EXPORT_CSV dataset if feature is enabled
        exported_models = current_app.config.get("EXPORT_CSV_MODELS", [])
        if "harvest" in exported_models:
            return redirect(get_export_url("harvest"))
        adapter = HarvestSourceCsvAdapter(get_csv_queryset(HarvestSource).order_by("created_at"))
        return csv.stream(adapter, "harvest")


@api.route("/site/context.jsonld", endpoint="site_jsonld_context")
class SiteJsonLdContext(API):
    def get(self):
        response = make_response(json.dumps(CONTEXT))
        response.headers["Content-Type"] = "application/ld+json"
        return response


def get_export_url(model):
    did = current_app.config["EXPORT_CSV_DATASET_ID"]
    dataset = Dataset.objects.get_or_404(id=did)
    resource = None
    for r in dataset.resources:
        if r.extras.get("csv-export:model", "") == model:
            resource = r
            break
    if not resource:
        api.abort(404)
    return resource.url
