from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from flask import current_app
from mongoengine import (
    DateTimeField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    StringField,
)

from udata.api_fields import field, generate_fields
from udata.core.user.models import User
from udata.mongo import db
from udata.mongo.encrypted_field import EncryptedStringField


def build_datasheet_url(datastore_id: str, datasheet_name: str) -> str:
    """URL of the datasheet's fiche on the cartes.gouv.fr dashboard."""
    base = current_app.config["GEOPF_DASHBOARD_BASE"]
    name = quote(datasheet_name, safe="")
    return f"{base}/tableau-de-bord/entrepots/{datastore_id}/donnees/{name}"


@generate_fields()
class GeopfDatasetPushMetadata(EmbeddedDocument):
    """Local state of a dataset's push to Géoplateforme."""

    datastore_id = field(
        StringField(),
        readonly=True,
        allow_null=True,
        description="The geopf datastore configured for this dataset's pushes",
    )
    # Internal only, hence not field-wrapped
    metadata_id = StringField()
    # The geopf `datasheet_name` tag grouping this dataset's entities into one
    # fiche. Frozen at first push so a later title change can't split the fiche.
    datasheet_name = StringField()

    @property
    @field(
        description="The cartes.gouv.fr fiche de données url for this dataset",
        allow_null=True,
    )
    def datasheet_url(self) -> str | None:
        if not (self.datastore_id and self.datasheet_name):
            return None
        return build_datasheet_url(self.datastore_id, self.datasheet_name)


@generate_fields()
class GeopfDatasetPullMetadata(EmbeddedDocument):
    """Local state of the last offering-pull run for a dataset."""

    status = field(
        StringField(choices=("pending", "done", "error")),
        readonly=True,
        allow_null=True,
        description="Pull status: null (never run), pending, done or error",
    )
    last_synced_at = field(
        DateTimeField(), readonly=True, allow_null=True, description="Last successful pull date"
    )
    error = field(
        StringField(), readonly=True, allow_null=True, description="The last pull error, if any"
    )
    task_id = field(
        StringField(), readonly=True, allow_null=True, description="The last pull Celery task's id"
    )


@generate_fields()
class GeopfDatasetMetadata(EmbeddedDocument):
    push = EmbeddedDocumentField(GeopfDatasetPushMetadata)
    pull = EmbeddedDocumentField(GeopfDatasetPullMetadata)


@generate_fields()
class GeopfResourcePushMetadata(EmbeddedDocument):
    """Local state of a resource's push to Géoplateforme."""

    status = field(
        StringField(choices=("pending", "done", "error", "timeout")),
        readonly=True,
        allow_null=True,
        description="Push status: null (never run), pending, done, error or timeout",
    )
    error = field(
        StringField(), readonly=True, allow_null=True, description="The last push error, if any"
    )
    task_id = field(
        StringField(), readonly=True, allow_null=True, description="The last push Celery task's id"
    )
    stored_data_id = field(
        StringField(),
        readonly=True,
        allow_null=True,
        description="The geopf stored_data id produced by the last push",
    )
    last_synced_at = field(
        DateTimeField(), readonly=True, allow_null=True, description="Last successful push date"
    )


@generate_fields()
class GeopfResourceOfferingMetadata(EmbeddedDocument):
    """Local state of a resource created from a pulled Géoplateforme offering."""

    id = field(StringField(), readonly=True, allow_null=True, description="The geopf offering id")
    last_synced_at = field(
        DateTimeField(),
        readonly=True,
        allow_null=True,
        description="Last successful pull date for this offering",
    )


class GeopfResourceMetadata(EmbeddedDocument):
    push = EmbeddedDocumentField(GeopfResourcePushMetadata)
    offering = EmbeddedDocumentField(GeopfResourceOfferingMetadata)


def dataset_push_metadata(dataset) -> GeopfDatasetPushMetadata:
    return (dataset.geopf and dataset.geopf.push) or GeopfDatasetPushMetadata()


def dataset_pull_metadata(dataset) -> GeopfDatasetPullMetadata:
    return (dataset.geopf and dataset.geopf.pull) or GeopfDatasetPullMetadata()


def resource_push_metadata(resource) -> GeopfResourcePushMetadata:
    return (resource.geopf and resource.geopf.push) or GeopfResourcePushMetadata()


def resource_offering_metadata(resource) -> GeopfResourceOfferingMetadata:
    return (resource.geopf and resource.geopf.offering) or GeopfResourceOfferingMetadata()


class GeopfToken(db.Document):
    """Per-user OAuth2 tokens used to call the Géoplateforme entrepôt API on their behalf.

    One token per data.gouv.fr user, obtained via the authorization_code flow
    against geopf's Keycloak (see udata/geopf/api.py) and refreshed as needed
    before each call (see udata/geopf/auth.py).
    """

    user = db.ReferenceField(User, required=True, unique=True, reverse_delete_rule=db.CASCADE)
    access_token = EncryptedStringField(key_config="GEOPF_TOKEN_ENCRYPTION_KEY", required=True)
    refresh_token = EncryptedStringField(key_config="GEOPF_TOKEN_ENCRYPTION_KEY", required=True)
    expires_at = db.DateTimeField(required=True)
    created_at = db.DateTimeField(default=lambda: datetime.now(UTC), required=True)

    meta = {"collection": "geopf_token"}

    def is_expired(self, within_seconds: int = 0) -> bool:
        """Whether the token is expired, or will be within `within_seconds`."""
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC) + timedelta(seconds=within_seconds)
