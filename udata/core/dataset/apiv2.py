import logging

import mongoengine
from flask import abort, request, url_for
from flask_restx import marshal

from udata import search
from udata.api import API, apiv2, fields
from udata.core.contact_point.api_fields import contact_point_fields
from udata.core.organization.api_fields import member_user_with_email_fields
from udata.core.spatial.api_fields import geojson
from udata.utils import get_by, multi_to_dict

from .api import ResourceMixin
from .api_fields import (
    badge_fields,
    catalog_schema_fields,
    checksum_fields,
    dataset_harvest_fields,
    dataset_internal_fields,
    org_ref_fields,
    resource_fields,
    resource_harvest_fields,
    resource_internal_fields,
    schema_fields,
    spatial_coverage_fields,
    temporal_coverage_fields,
    user_ref_fields,
)
from .constants import DEFAULT_FREQUENCY, DEFAULT_LICENSE, UPDATE_FREQUENCIES
from .models import CommunityResource, Dataset
from .permissions import DatasetEditPermission, ResourceEditPermission
from .search import DatasetSearch

DEFAULT_PAGE_SIZE = 50

#: Default mask to make it lightweight by default
DEFAULT_MASK_APIV2 = ",".join(
    (
        "id",
        "title",
        "acronym",
        "slug",
        "description",
        "created_at",
        "last_modified",
        "deleted",
        "private",
        "tags",
        "badges",
        "resources",
        "community_resources",
        "frequency",
        "frequency_date",
        "extras",
        "metrics",
        "organization",
        "owner",
        "temporal_coverage",
        "spatial",
        "license",
        "uri",
        "page",
        "last_update",
        "archived",
        "quality",
        "harvest",
        "internal",
        "contact_point",
    )
)

log = logging.getLogger(__name__)

ns = apiv2.namespace("datasets", "Dataset related operations")
search_parser = DatasetSearch.as_request_parser()
resources_parser = apiv2.parser()
resources_parser.add_argument(
    "page", type=int, default=1, location="args", help="The page to fetch"
)
resources_parser.add_argument(
    "page_size", type=int, default=DEFAULT_PAGE_SIZE, location="args", help="The page size to fetch"
)
resources_parser.add_argument(
    "type", type=str, location="args", help="The type of resources to fetch"
)
resources_parser.add_argument(
    "q", type=str, location="args", help="query string to search through resources titles"
)

common_doc = {"params": {"dataset": "The dataset ID or slug"}}


dataset_fields = apiv2.model(
    "Dataset",
    {
        "id": fields.String(description="The dataset identifier", readonly=True),
        "title": fields.String(description="The dataset title", required=True),
        "acronym": fields.String(description="An optional dataset acronym"),
        "slug": fields.String(description="The dataset permalink string", required=True),
        "description": fields.Markdown(
            description="The dataset description in markdown", required=True
        ),
        "created_at": fields.ISODateTime(
            description="The dataset creation date", required=True, readonly=True
        ),
        "last_modified": fields.ISODateTime(
            description="The dataset last modification date", required=True, readonly=True
        ),
        "deleted": fields.ISODateTime(description="The deletion date if deleted", readonly=True),
        "archived": fields.ISODateTime(description="The archival date if archived"),
        "featured": fields.Boolean(description="Is the dataset featured"),
        "private": fields.Boolean(
            description="Is the dataset private to the owner or the organization"
        ),
        "tags": fields.List(fields.String),
        "badges": fields.List(
            fields.Nested(badge_fields), description="The dataset badges", readonly=True
        ),
        "resources": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "apiv2.resources",
                    dataset=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                "total": len(o.resources),
            },
            description="Link to the dataset resources",
        ),
        "community_resources": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "api.community_resources",
                    dataset=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                "total": len(o.community_resources),
            },
            description="Link to the dataset community resources",
        ),
        "frequency": fields.String(
            description="The update frequency",
            required=True,
            enum=list(UPDATE_FREQUENCIES),
            default=DEFAULT_FREQUENCY,
        ),
        "frequency_date": fields.ISODateTime(
            description=(
                "Next expected update date, you will be notified " "once that date is reached."
            )
        ),
        "harvest": fields.Nested(
            dataset_harvest_fields,
            readonly=True,
            allow_null=True,
            description="Dataset harvest metadata attributes",
            skip_none=True,
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
        "metrics": fields.Raw(
            attribute=lambda o: o.get_metrics(), description="The dataset metrics"
        ),
        "organization": fields.Nested(
            org_ref_fields, allow_null=True, description="The producer organization"
        ),
        "owner": fields.Nested(
            user_ref_fields, allow_null=True, description="The user information"
        ),
        "temporal_coverage": fields.Nested(
            temporal_coverage_fields, allow_null=True, description="The temporal coverage"
        ),
        "spatial": fields.Nested(
            spatial_coverage_fields, allow_null=True, description="The spatial coverage"
        ),
        "license": fields.String(
            attribute="license.id", default=DEFAULT_LICENSE["id"], description="The dataset license"
        ),
        "uri": fields.UrlFor(
            "api.dataset",
            lambda o: {"dataset": o},
            description="The dataset API URI",
            required=True,
        ),
        "page": fields.UrlFor(
            "datasets.show",
            lambda o: {"dataset": o},
            description="The dataset page URL",
            required=True,
            fallback_endpoint="api.dataset",
        ),
        "quality": fields.Raw(description="The dataset quality", readonly=True),
        "last_update": fields.ISODateTime(
            description="The resources last modification date", required=True
        ),
        "internal": fields.Nested(
            dataset_internal_fields,
            readonly=True,
            description="Site internal and specific object's data",
        ),
        "contact_point": fields.Nested(
            contact_point_fields, allow_null=True, description="The dataset's contact point"
        ),
    },
    mask=DEFAULT_MASK_APIV2,
)


resource_page_fields = apiv2.model(
    "ResourcePage",
    {
        "data": fields.List(fields.Nested(resource_fields, description="The dataset resources")),
        "next_page": fields.String(),
        "previous_page": fields.String(),
        "page": fields.Integer(),
        "page_size": fields.Integer(),
        "total": fields.Integer(),
    },
)

dataset_page_fields = apiv2.model(
    "DatasetPage", fields.pager(dataset_fields), mask="data{{{0}}},*".format(DEFAULT_MASK_APIV2)
)

specific_resource_fields = apiv2.model(
    "SpecificResource",
    {
        "resource": fields.Nested(resource_fields, description="The dataset resources"),
        "dataset_id": fields.String(),
    },
)

apiv2.inherit("Badge", badge_fields)
apiv2.inherit("OrganizationReference", org_ref_fields)
apiv2.inherit("UserReference", user_ref_fields)
apiv2.inherit("MemberUserWithEmail", member_user_with_email_fields)
apiv2.inherit("Resource", resource_fields)
apiv2.inherit("SpatialCoverage", spatial_coverage_fields)
apiv2.inherit("TemporalCoverage", temporal_coverage_fields)
apiv2.inherit("GeoJSON", geojson)
apiv2.inherit("Checksum", checksum_fields)
apiv2.inherit("HarvestDatasetMetadata", dataset_harvest_fields)
apiv2.inherit("HarvestResourceMetadata", resource_harvest_fields)
apiv2.inherit("DatasetInternals", dataset_internal_fields)
apiv2.inherit("ResourceInternals", resource_internal_fields)
apiv2.inherit("ContactPoint", contact_point_fields)
apiv2.inherit("Schema", schema_fields)
apiv2.inherit("CatalogSchema", catalog_schema_fields)


@ns.route("/search/", endpoint="dataset_search")
class DatasetSearchAPI(API):
    """Datasets collection search endpoint"""

    @apiv2.doc("search_datasets")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(dataset_page_fields)
    def get(self):
        """List or search all datasets"""
        search_parser.parse_args()
        try:
            return search.query(Dataset, **multi_to_dict(request.args))
        except NotImplementedError:
            abort(501, "Search endpoint not enabled")
        except RuntimeError:
            abort(500, "Internal search service error")


@ns.route("/<dataset:dataset>/", endpoint="dataset", doc=common_doc)
@apiv2.response(404, "Dataset not found")
@apiv2.response(410, "Dataset has been deleted")
class DatasetAPI(API):
    @apiv2.doc("get_dataset")
    @apiv2.marshal_with(dataset_fields)
    def get(self, dataset):
        """Get a dataset given its identifier"""
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            apiv2.abort(410, "Dataset has been deleted")
        return dataset


@ns.route("/<dataset:dataset>/extras/", endpoint="dataset_extras", doc=common_doc)
@apiv2.response(400, "Wrong payload format, dict expected")
@apiv2.response(400, "Wrong payload format, list expected")
@apiv2.response(404, "Dataset not found")
@apiv2.response(410, "Dataset has been deleted")
class DatasetExtrasAPI(API):
    @apiv2.doc("get_dataset_extras")
    def get(self, dataset):
        """Get a dataset extras given its identifier"""
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            apiv2.abort(410, "Dataset has been deleted")
        return dataset.extras

    @apiv2.secure
    @apiv2.doc("update_dataset_extras")
    def put(self, dataset):
        """Update a given dataset extras"""
        data = request.json
        if not isinstance(data, dict):
            apiv2.abort(400, "Wrong payload format, dict expected")
        if dataset.deleted:
            apiv2.abort(410, "Dataset has been deleted")
        DatasetEditPermission(dataset).test()
        # first remove extras key associated to a None value in payload
        for key in [k for k in data if data[k] is None]:
            dataset.extras.pop(key, None)
            data.pop(key)
        # then update the extras with the remaining payload
        dataset.extras.update(data)
        try:
            dataset.save(signal_kwargs={"ignores": ["post_save"]})
        except mongoengine.errors.ValidationError as e:
            apiv2.abort(400, e.message)
        return dataset.extras

    @apiv2.secure
    @apiv2.doc("delete_dataset_extras")
    def delete(self, dataset):
        """Delete a given dataset extras key on a given dataset"""
        data = request.json
        if not isinstance(data, list):
            apiv2.abort(400, "Wrong payload format, list expected")
        if dataset.deleted:
            apiv2.abort(410, "Dataset has been deleted")
        DatasetEditPermission(dataset).test()
        for key in data:
            try:
                del dataset.extras[key]
            except KeyError:
                pass
        dataset.save(signal_kwargs={"ignores": ["post_save"]})
        return dataset.extras, 204


@ns.route("/<dataset:dataset>/resources/", endpoint="resources")
class ResourcesAPI(API):
    @apiv2.doc("list_resources")
    @apiv2.expect(resources_parser)
    @apiv2.marshal_with(resource_page_fields)
    def get(self, dataset):
        """Get the given dataset resources, paginated."""
        args = resources_parser.parse_args()
        page = args["page"]
        page_size = args["page_size"]
        list_resources_url = url_for("apiv2.resources", dataset=dataset.id, _external=True)
        next_page = f"{list_resources_url}?page={page + 1}&page_size={page_size}"
        previous_page = f"{list_resources_url}?page={page - 1}&page_size={page_size}"
        res = dataset.resources

        if args["type"]:
            res = [elem for elem in res if elem["type"] == args["type"]]
            next_page += f"&type={args['type']}"
            previous_page += f"&type={args['type']}"

        if args["q"]:
            res = [elem for elem in res if args["q"].lower() in elem["title"].lower()]
            next_page += f"&q={args['q']}"
            previous_page += f"&q={args['q']}"

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0
        paginated_result = res[offset : (page_size + offset if page_size is not None else None)]

        return {
            "data": paginated_result,
            "next_page": next_page if page_size + offset < len(res) else None,
            "page": page,
            "page_size": page_size,
            "previous_page": previous_page if page > 1 else None,
            "total": len(res),
        }


@ns.route("/resources/<uuid:rid>/", endpoint="resource")
class ResourceAPI(API):
    @apiv2.doc("get_resource")
    def get(self, rid):
        dataset = Dataset.objects(resources__id=rid).first()
        if dataset:
            resource = get_by(dataset.resources, "id", rid)
        else:
            resource = CommunityResource.objects(id=rid).first()
        if not resource:
            apiv2.abort(404, "Resource does not exist")

        # Manually marshalling to make sure resource.dataset is in the scope.
        # See discussions in https://github.com/opendatateam/udata/pull/2732/files
        return marshal(
            {"resource": resource, "dataset_id": dataset.id if dataset else None},
            specific_resource_fields,
        )


@ns.route(
    "/<dataset:dataset>/resources/<uuid:rid>/extras/", endpoint="resource_extras", doc=common_doc
)
@apiv2.param("rid", "The resource unique identifier")
@apiv2.response(400, "Wrong payload format, dict expected")
@apiv2.response(400, "Wrong payload format, list expected")
@apiv2.response(404, "Key not found in existing extras")
@apiv2.response(410, "Dataset has been deleted")
class ResourceExtrasAPI(ResourceMixin, API):
    @apiv2.doc("get_resource_extras")
    def get(self, dataset, rid):
        """Get a resource extras given its identifier"""
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            apiv2.abort(410, "Dataset has been deleted")
        resource = self.get_resource_or_404(dataset, rid)
        return resource.extras

    @apiv2.secure
    @apiv2.doc("update_resource_extras")
    def put(self, dataset, rid):
        """Update a given resource extras on a given dataset"""
        data = request.json
        if not isinstance(data, dict):
            apiv2.abort(400, "Wrong payload format, dict expected")
        if dataset.deleted:
            apiv2.abort(410, "Dataset has been deleted")
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        # first remove extras key associated to a None value in payload
        for key in [k for k in data if data[k] is None]:
            resource.extras.pop(key, None)
            data.pop(key)
        # then update the extras with the remaining payload
        resource.extras.update(data)
        resource.save(signal_kwargs={"ignores": ["post_save"]})
        return resource.extras

    @apiv2.secure
    @apiv2.doc("delete_resource_extras")
    def delete(self, dataset, rid):
        """Delete a given resource extras key on a given dataset"""
        data = request.json
        if not isinstance(data, list):
            apiv2.abort(400, "Wrong payload format, list expected")
        if dataset.deleted:
            apiv2.abort(410, "Dataset has been deleted")
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        try:
            for key in data:
                del resource.extras[key]
        except KeyError:
            apiv2.abort(404, "Key not found in existing extras")
        resource.save(signal_kwargs={"ignores": ["post_save"]})
        return resource.extras, 204
