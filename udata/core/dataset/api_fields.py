from udata.api import api, base_reference, fields
from udata.core.badges.fields import badge_fields
from udata.core.contact_point.api_fields import contact_point_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.constants import BIGGEST_LOGO_SIZE
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.user.api_fields import user_ref_fields

from .constants import (
    CHECKSUM_TYPES,
    DEFAULT_CHECKSUM_TYPE,
    DEFAULT_FREQUENCY,
    DEFAULT_LICENSE,
    RESOURCE_FILETYPES,
    RESOURCE_TYPES,
    UPDATE_FREQUENCIES,
)

checksum_fields = api.model(
    "Checksum",
    {
        "type": fields.String(
            description="The hashing algorithm used to compute the checksum",
            default=DEFAULT_CHECKSUM_TYPE,
            enum=CHECKSUM_TYPES,
        ),
        "value": fields.String(description="The resulting checksum/hash", required=True),
    },
)

# Use for schema inside Dataset or Resource
schema_fields = api.model(
    "Schema",
    {
        "name": fields.String(),
        "version": fields.String(),
        "url": fields.String(),
    },
)

dataset_harvest_fields = api.model(
    "HarvestDatasetMetadata",
    {
        "backend": fields.String(description="Harvest backend used", allow_null=True),
        "created_at": fields.ISODateTime(
            description="The dataset harvested creation date", allow_null=True, readonly=True
        ),
        "modified_at": fields.ISODateTime(
            description="The dataset harvest last modification date", allow_null=True, readonly=True
        ),
        "source_id": fields.String(description="The harvester id", allow_null=True),
        "remote_id": fields.String(
            description="The dataset remote id on the source portal", allow_null=True
        ),
        "domain": fields.String(description="The harvested domain", allow_null=True),
        "last_update": fields.ISODateTime(description="The last harvest date", allow_null=True),
        "remote_url": fields.String(description="The dataset remote url", allow_null=True),
        "uri": fields.String(description="The dataset harveted uri", allow_null=True),
        "dct_identifier": fields.String(
            description="The dct:identifier property from the harvested dataset", allow_null=True
        ),
        "archived_at": fields.ISODateTime(description="The archive date", allow_null=True),
        "archived": fields.String(
            description="The reason the dataset has been archived", allow_null=True
        ),
    },
)

resource_harvest_fields = api.model(
    "HarvestResourceMetadata",
    {
        "created_at": fields.ISODateTime(
            description="The resource harvested creation date", allow_null=True, readonly=True
        ),
        "modified_at": fields.ISODateTime(
            description="The resource harvest last modification date",
            allow_null=True,
            readonly=True,
        ),
        "uri": fields.String(description="The resource harvest uri", allow_null=True),
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

resource_internal_fields = api.model(
    "ResourceInternals",
    {
        "created_at_internal": fields.ISODateTime(
            description="The resource's internal creation date on the site", required=True
        ),
        "last_modified_internal": fields.ISODateTime(
            description="The resource's internal last modification date", required=True
        ),
    },
)

resource_fields = api.model(
    "Resource",
    {
        "id": fields.String(description="The resource unique ID", readonly=True),
        "title": fields.String(description="The resource title", required=True),
        "description": fields.Markdown(description="The resource markdown description"),
        "filetype": fields.String(
            description=("Whether the resource is an uploaded file, a remote file or an API"),
            required=True,
            enum=list(RESOURCE_FILETYPES),
        ),
        "type": fields.String(
            description=("Resource type (documentation, API...)"),
            required=True,
            enum=list(RESOURCE_TYPES),
        ),
        "format": fields.String(description="The resource format", required=True),
        "url": fields.String(description="The resource URL", required=True),
        "latest": fields.String(
            description="The permanent URL redirecting to "
            "the latest version of the resource. When the "
            "resource data is updated, the URL will "
            "change, the latest URL won't.",
            readonly=True,
        ),
        "checksum": fields.Nested(
            checksum_fields, allow_null=True, description="A checksum to validate file validity"
        ),
        "filesize": fields.Integer(description="The resource file size in bytes"),
        "mime": fields.String(description="The resource mime type"),
        "created_at": fields.ISODateTime(readonly=True, description="The resource creation date"),
        "last_modified": fields.ISODateTime(
            readonly=True, description="The resource last modification date"
        ),
        "metrics": fields.Raw(description="The resource metrics", readonly=True),
        "harvest": fields.Nested(
            resource_harvest_fields,
            allow_null=True,
            readonly=True,
            description="Harvest attributes metadata information",
            skip_none=True,
        ),
        "extras": fields.Raw(description="Extra attributes as key-value pairs"),
        "preview_url": fields.String(
            description="An optional preview URL to be "
            "loaded as a standalone page (ie. iframe or "
            "new page)",
            readonly=True,
        ),
        "schema": fields.Nested(
            schema_fields, allow_null=True, description="Reference to the associated schema"
        ),
        "internal": fields.Nested(
            resource_internal_fields,
            readonly=True,
            description="Site internal and specific object's data",
        ),
    },
)

upload_fields = api.inherit(
    "UploadedResource",
    resource_fields,
    {
        "success": fields.Boolean(
            description="Whether the upload succeeded or not.", readonly=True, default=True
        ),
    },
)

resources_order = api.as_list(fields.String(description="Resource ID"))

temporal_coverage_fields = api.model(
    "TemporalCoverage",
    {
        "start": fields.ISODateTime(description="The temporal coverage start date", required=True),
        "end": fields.ISODateTime(description="The temporal coverage end date"),
    },
)

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
    resource_fields,
    {
        "dataset": fields.Nested(
            dataset_ref_fields, allow_null=True, description="Reference to the associated dataset"
        ),
        "organization": fields.Nested(
            org_ref_fields, allow_null=True, description="The producer organization"
        ),
        "owner": fields.Nested(
            user_ref_fields, allow_null=True, description="The user information"
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
        "metrics",
        "organization",
        "owner",
        "schema",
        "temporal_coverage",
        "spatial",
        "license",
        "uri",
        "page",
        "last_update",
        "archived",
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
        "slug": fields.String(description="The dataset permalink string", required=True),
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
        "featured": fields.Boolean(description="Is the dataset featured"),
        "private": fields.Boolean(
            description="Is the dataset private to the owner or the organization"
        ),
        "tags": fields.List(fields.String),
        "badges": fields.List(
            fields.Nested(badge_fields), description="The dataset badges", readonly=True
        ),
        "resources": fields.List(
            fields.Nested(resource_fields, description="The dataset resources")
        ),
        "community_resources": fields.List(
            fields.Nested(
                community_resource_fields, description="The dataset community submitted resources"
            )
        ),
        "frequency": fields.String(
            description="The update frequency",
            required=True,
            enum=list(UPDATE_FREQUENCIES),
            default=DEFAULT_FREQUENCY,
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
            schema_fields, allow_null=True, description="Reference to the associated schema"
        ),
        "internal": fields.Nested(
            dataset_internal_fields,
            readonly=True,
            description="Site internal and specific object's data",
        ),
        "contact_points": fields.List(
            fields.Nested(contact_point_fields, description="The dataset contact points"),
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
