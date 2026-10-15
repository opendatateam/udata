from udata.api import api, base_reference, fields
from udata.core.access_type.models import AccessAudience
from udata.core.badges.models import Badge
from udata.core.contact_point.models import ContactPoint
from udata.core.organization.constants import BIGGEST_LOGO_SIZE
from udata.core.organization.models import Organization
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.user.models import User

from .constants import DEFAULT_LICENSE, UpdateFrequency
from .models import Resource, Schema, temporal_coverage_fields

dataset_harvest_fields = api.model(
    "HarvestDatasetMetadata",
    {
        "backend": fields.String(description="Harvest backend used", allow_null=True),
        "domain": fields.String(description="The harvested domain", allow_null=True),
        "source_id": fields.String(description="The harvester id", allow_null=True),
        "source_url": fields.String(description="The harvester source url", allow_null=True),
        "remote_id": fields.String(
            description="The dataset remote id on the source portal", allow_null=True
        ),
        "remote_url": fields.String(description="The dataset remote url", allow_null=True),
        "created_at": fields.ISODateTime(
            description="The dataset harvested creation date", allow_null=True, readonly=True
        ),
        "issued_at": fields.ISODateTime(
            description="The dataset harvested release date", allow_null=True, readonly=True
        ),
        "modified_at": fields.ISODateTime(
            description="The dataset harvest last modification date", allow_null=True, readonly=True
        ),
        "last_update": fields.ISODateTime(
            description="The dataset last harvest date", allow_null=True
        ),
        "archived_at": fields.ISODateTime(description="The archive date", allow_null=True),
        "archived_reason": fields.String(
            description="The reason the dataset has been archived", allow_null=True
        ),
        "uri": fields.String(description="The dataset harveted uri", allow_null=True),
        "dct_identifier": fields.String(
            description="The dct:identifier property from the harvested dataset", allow_null=True
        ),
        "doi": fields.String(
            description="The DOI the source declares for the dataset (dct:identifier, "
            "adms:identifier or owl:sameAs)",
            allow_null=True,
            readonly=True,
        ),
    },
)

dataset_geopf_fields = api.model(
    "GeopfDatasetMetadata",
    {
        "datasheet_url": fields.String(
            attribute="push.datasheet_url",
            description="Public Géoplateforme fiche (dashboard) url, once pushed",
            allow_null=True,
            readonly=True,
        ),
    },
)

license_fields = api.model(
    "License",
    {
        "id": fields.String(description="The license identifier", required=True),
        "title": fields.String(description="The resource title", required=True),
        "maintainer": fields.String(description="The license official maintainer"),
        "url": fields.String(description="The license official URL"),
        "flags": fields.List(fields.String, description="Some arbitry flags"),
        "alternate_urls": fields.List(
            fields.String, description="Same alternative known URLs (improve rematch)"
        ),
        "alternate_titles": fields.List(
            fields.String, description="Same alternative known titles (improve rematch)"
        ),
    },
)

frequency_fields = api.model(
    "Frequency",
    {
        "id": fields.String(description="The frequency identifier"),
        "label": fields.String(description="The frequency display name"),
    },
)

upload_fields = api.inherit(
    "UploadedResource",
    Resource.__read_fields__,
    {
        "success": fields.Boolean(
            description="Whether the upload succeeded or not.", readonly=True, default=True
        ),
    },
)

resources_order = api.as_list(fields.String(description="Resource ID"))

dataset_ref_fields = api.inherit(
    "DatasetReference",
    base_reference,
    {
        "title": fields.String(description="The dataset title", readonly=True),
        "acronym": fields.String(description="An optional dataset acronym", readonly=True),
        "uri": fields.String(
            attribute=lambda d: d.self_api_url(),
            description="The API URI for this dataset",
            readonly=True,
        ),
        "page": fields.String(
            attribute=lambda d: d.self_web_url(),
            description="The dataset web page URL",
            readonly=True,
        ),
    },
)


community_resource_permissions_fields = api.model(
    "DatasetPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)

community_resource_fields = api.inherit(
    "CommunityResource",
    Resource.__read_fields__,
    {
        "dataset": fields.Nested(
            dataset_ref_fields, allow_null=True, description="Reference to the associated dataset"
        ),
        "organization": fields.Nested(
            Organization.__ref_fields__, allow_null=True, description="The producer organization"
        ),
        "owner": fields.Nested(
            User.__ref_fields__, allow_null=True, description="The user information"
        ),
        "permissions": fields.Nested(community_resource_permissions_fields),
    },
)


upload_community_fields = api.inherit(
    "UploadedCommunityResource",
    community_resource_fields,
    {
        "success": fields.Boolean(
            description="Whether the upload succeeded or not.", readonly=True, default=True
        ),
    },
)

community_resource_page_fields = api.model(
    "CommunityResourcePage", fields.pager(community_resource_fields)
)

#: Default mask to make it lightweight by default
DEFAULT_MASK = ",".join(
    (
        "id",
        "title",
        "acronym",
        "slug",
        "description",
        "description_short",
        "created_at",
        "last_modified",
        "deleted",
        "private",
        "tags",
        "badges",
        "resources",
        "frequency",
        "frequency_date",
        "extras",
        "harvest",
        "geopf",
        "metrics",
        "organization",
        "owner",
        "schema",
        "temporal_coverage",
        "spatial",
        "license",
        "access_type",
        "access_audiences",
        "authorization_request_url",
        "access_type_reason_category",
        "access_type_reason",
        "uri",
        "page",
        "last_update",
        "archived",
        "doi",
        "quality",
        "internal",
        "contact_points",
        "featured",
        "permissions",
    )
)

dataset_internal_fields = api.model(
    "DatasetInternals",
    {
        "created_at_internal": fields.ISODateTime(
            description="The dataset's internal creation date on the site", required=True
        ),
        "last_modified_internal": fields.ISODateTime(
            description="The dataset's internal last modification date", required=True
        ),
    },
)

dataset_permissions_fields = api.model(
    "DatasetPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
        "edit_resources": fields.Permission(),
    },
)

dataset_fields = api.model(
    "Dataset",
    {
        "id": fields.String(description="The dataset identifier", readonly=True),
        "title": fields.String(description="The dataset title", required=True),
        "acronym": fields.String(description="An optional dataset acronym"),
        "slug": fields.String(description="The dataset permalink string", readonly=True),
        "description": fields.Markdown(
            description="The dataset description in markdown", required=True
        ),
        "description_short": fields.String(description="The dataset short description"),
        "created_at": fields.ISODateTime(
            description="This date is computed between harvested creation date if any and site's internal creation date",
            required=True,
            readonly=True,
        ),
        "last_modified": fields.ISODateTime(
            description="The dataset last modification date", required=True, readonly=True
        ),
        "deleted": fields.ISODateTime(description="The deletion date if deleted", readonly=True),
        "archived": fields.ISODateTime(description="The archival date if archived"),
        "doi": fields.String(description="The DOI minted for this dataset", readonly=True),
        "featured": fields.Boolean(description="Is the dataset featured"),
        "private": fields.Boolean(
            description="Is the dataset private to the owner or the organization"
        ),
        "tags": fields.List(fields.String),
        "badges": fields.List(
            fields.Nested(Badge.__read_fields__), description="The dataset badges", readonly=True
        ),
        "resources": fields.List(
            fields.Nested(Resource.__read_fields__, description="The dataset resources")
        ),
        "community_resources": fields.List(
            fields.Nested(
                community_resource_fields, description="The dataset community submitted resources"
            )
        ),
        "frequency": fields.String(
            description="The update frequency",
            required=True,
            enum=list(UpdateFrequency),
            default=UpdateFrequency.UNKNOWN,
        ),
        "frequency_date": fields.ISODateTime(
            description=(
                "Next expected update date, you will be notified once that date is reached."
            )
        ),
        "harvest": fields.Nested(
            dataset_harvest_fields,
            readonly=True,
            allow_null=True,
            description="Dataset harvest metadata attributes",
            skip_none=True,
        ),
        "geopf": fields.Nested(
            dataset_geopf_fields,
            readonly=True,
            allow_null=True,
            description="Géoplateforme sync status metadata",
            skip_none=True,
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
        "metrics": fields.Raw(
            attribute=lambda o: o.get_metrics(), description="The dataset metrics"
        ),
        "organization": fields.Nested(
            Organization.__ref_fields__, allow_null=True, description="The producer organization"
        ),
        "owner": fields.Nested(
            User.__ref_fields__, allow_null=True, description="The user information"
        ),
        "temporal_coverage": fields.Nested(
            temporal_coverage_fields,
            allow_null=True,
            description="The temporal coverage",
        ),
        "spatial": fields.Nested(
            spatial_coverage_fields, allow_null=True, description="The spatial coverage"
        ),
        "license": fields.String(
            attribute="license.id", default=DEFAULT_LICENSE["id"], description="The dataset license"
        ),
        "access_type": fields.String(allow_null=True),
        "access_audiences": fields.List(fields.Nested(AccessAudience.__read_fields__)),
        "authorization_request_url": fields.String(allow_null=True),
        "access_type_reason_category": fields.String(allow_null=True),
        "access_type_reason": fields.String(allow_null=True),
        "uri": fields.String(
            attribute=lambda d: d.self_api_url(),
            description="The API URI for this dataset",
            readonly=True,
        ),
        "page": fields.String(
            attribute=lambda d: d.self_web_url(),
            description="The dataset web page URL",
            readonly=True,
        ),
        "quality": fields.Raw(description="The dataset quality", readonly=True),
        "last_update": fields.ISODateTime(
            description="The resources last modification date", required=True
        ),
        "schema": fields.Nested(
            Schema.__read_fields__,
            allow_null=True,
            description="Reference to the associated schema",
        ),
        "internal": fields.Nested(
            dataset_internal_fields,
            readonly=True,
            description="Site internal and specific object's data",
        ),
        "contact_points": fields.List(
            fields.Nested(ContactPoint.__read_fields__, description="The dataset contact points"),
        ),
        "permissions": fields.Nested(dataset_permissions_fields),
    },
    mask=DEFAULT_MASK,
)

dataset_page_fields = api.model(
    "DatasetPage", fields.pager(dataset_fields), mask="data{{{0}}},*".format(DEFAULT_MASK)
)


dataset_suggestion_fields = api.model(
    "DatasetSuggestion",
    {
        "id": fields.String(description="The dataset identifier"),
        "title": fields.String(description="The dataset title"),
        "acronym": fields.String(description="An optional dataset acronym"),
        "slug": fields.String(description="The dataset permalink string"),
        "image_url": fields.ImageField(
            size=BIGGEST_LOGO_SIZE, description="The dataset (organization) logo URL", readonly=True
        ),
        "page": fields.String(description="The dataset web page URL", readonly=True),
    },
)


resource_type_fields = api.model(
    "ResourceType",
    {
        "id": fields.String(description="The resource type identifier"),
        "label": fields.String(description="The resource type display name"),
    },
)

# follow the specification of https://schema.data.gouv.fr/schemas/schemas.json
catalog_schema_fields = api.model(
    "CatalogSchema",
    {
        "name": fields.String(),
        "title": fields.String(),
        "description": fields.String(),
        "schema_url": fields.String(description="Often the link to the latest version"),
        "schema_type": fields.String(enum=["tableschema", "datapackage", "jsonschema", "other"]),
        "contact": fields.String(),
        "examples": fields.List(
            fields.Nested(
                api.model(
                    "CatalogSchemaExample",
                    {
                        "title": fields.String(),
                        "path": fields.String(),
                    },
                )
            )
        ),
        "labels": fields.List(fields.String()),
        "consolidation_dataset_id": fields.String(),
        "versions": fields.List(
            fields.Nested(
                api.model(
                    "CatalogSchemaVersion",
                    {
                        "version_name": fields.String(),
                        "schema_url": fields.String(),
                    },
                )
            )
        ),
        "external_doc": fields.String(),
        "external_tool": fields.String(
            description="Link to tools to create a file with this schema"
        ),
        "homepage": fields.String(),
        "datapackage_title": fields.String(
            description="Only present if the schema is inside a datapackage"
        ),
        "datapackage_name": fields.String(
            description="Only present if the schema is inside a datapackage"
        ),
        "datapackage_description": fields.String(
            description="Only present if the schema is inside a datapackage"
        ),
    },
)
