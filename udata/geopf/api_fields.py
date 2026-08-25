from udata.api import api, fields
from udata.geopf.models import GeopfDatasetPullMetadata, GeopfResourcePushMetadata

geopf_status_fields = api.model(
    "GeopfStatus",
    {
        "connected": fields.Boolean(
            description="Whether the current user has an active, usable geopf link"
        ),
        "expires_at": fields.String(
            description="The stored geopf token's expiration date", allow_null=True
        ),
    },
)

geopf_push_status_fields = GeopfResourcePushMetadata.__read_fields__
geopf_pull_status_fields = GeopfDatasetPullMetadata.__read_fields__

geopf_pushable_resource_fields = api.model(
    "GeopfPushableResource",
    {
        "id": fields.String(description="The resource id"),
        "title": fields.String(description="The resource title"),
        "format": fields.String(description="The resource format"),
        "url": fields.String(description="The resource url"),
        "push": fields.Nested(geopf_push_status_fields),
    },
)

geopf_offering_resource_fields = api.model(
    "GeopfOfferingResource",
    {
        "id": fields.String(description="The resource id"),
        "title": fields.String(description="The resource title"),
        "format": fields.String(description="The resource format"),
        "url": fields.String(description="The resource url"),
        "offering_id": fields.String(description="The geopf offering id"),
        "last_synced_at": fields.ISODateTime(
            description="Last successful pull date for this offering", allow_null=True
        ),
    },
)

geopf_dataset_status_fields = api.model(
    "GeopfDatasetStatus",
    {
        "datastore_id": fields.String(
            description="The geopf datastore configured for this dataset's pushes",
            allow_null=True,
        ),
        "fiche_url": fields.String(
            description="The cartes.gouv.fr fiche de données url for this dataset", allow_null=True
        ),
        "pull": fields.Nested(geopf_pull_status_fields),
        "pushable": fields.List(
            fields.Nested(geopf_pushable_resource_fields),
            description="Resources eligible for a push",
        ),
        "offerings": fields.List(
            fields.Nested(geopf_offering_resource_fields),
            description="Resources that came back from a pull as geopf offerings",
        ),
    },
)

geopf_datastore_fields = api.model(
    "GeopfDatastore",
    {
        "datastore_id": fields.String(description="The datastore id"),
        "name": fields.String(description="The datastore display name", allow_null=True),
        "rights": fields.List(
            fields.String, description="The current user's rights on this datastore"
        ),
    },
)

geopf_push_request_fields = api.model(
    "GeopfPushRequest",
    {
        "datastore_id": fields.String(
            description=(
                "The datastore to push to. Optional if the dataset already has one "
                "configured from a previous push."
            ),
            required=False,
        ),
    },
    location="json",
)

geopf_task_fields = api.model(
    "GeopfTask",
    {
        "task_id": fields.String(description="The id of the enqueued Celery task"),
    },
)
