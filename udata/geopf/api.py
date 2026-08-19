import mongoengine
from flask import current_app, redirect, request, session, url_for

from udata.api import API, api
from udata.auth import current_user
from udata.core.dataset.models import Dataset
from udata.uris import cdata_url, homepage_url
from udata.utils import get_by

from .auth import oauth, resolve_access_token, revoke_token, store_token
from .client import GeopfClient, GeopfError, GeopfReauthRequired
from .models import GeopfToken
from .tasks import (
    pull_offerings_from_geopf,
    push_resource_to_geopf,
    set_dataset_extras,
    set_resource_extras,
)

ns = api.namespace("geopf", "Géoplateforme related operations")

DATASET_SESSION_KEY = "geopf_oauth_dataset_id"


def _redirect_target(dataset_id: str | None) -> str:
    """Resolve a dataset id to its cdata admin geopf page, falling back to the homepage."""
    if dataset_id:
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            url = cdata_url(f"/admin/datasets/{dataset.id}/geopf", flash="connected")
            if url:
                return url
        except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
            pass
    return homepage_url(flash="connected")


@ns.route("/login/", endpoint="geopf_login")
class GeopfLoginAPI(API):
    @api.secure
    @api.doc("geopf_login")
    def get(self):
        """Start the OAuth link between the current user and their geopf identity."""
        session[DATASET_SESSION_KEY] = request.args.get("dataset_id")
        redirect_uri = url_for("api.geopf_auth", _external=True)
        return oauth.geopf.authorize_redirect(redirect_uri)


@ns.route("/auth", endpoint="geopf_auth")
class GeopfAuthAPI(API):
    @api.secure
    @api.doc("geopf_auth")
    def get(self):
        """OAuth callback: exchange the code, persist the token, bounce back to cdata."""
        token = oauth.geopf.authorize_access_token()
        store_token(current_user._get_current_object(), token)
        dataset_id = session.pop(DATASET_SESSION_KEY, None)
        return redirect(_redirect_target(dataset_id))


@ns.route("/status/", endpoint="geopf_status")
class GeopfStatusAPI(API):
    @api.secure
    @api.doc("geopf_status")
    def get(self):
        """Whether the current user has an active, usable geopf link.

        A stored token whose access token is merely expired still counts as
        connected (it gets refreshed here as a side effect); only a token
        that can no longer be refreshed reports as disconnected.
        """
        try:
            resolve_access_token(user=current_user._get_current_object())
        except GeopfReauthRequired:
            return {"connected": False, "expires_at": None}
        geopf_token = GeopfToken.objects(user=current_user.id).first()
        return {"connected": True, "expires_at": geopf_token.expires_at.isoformat()}


def _resource_summary(resource) -> dict:
    """The resource fields the geopf sync UI needs to render a row."""
    return {
        "id": str(resource.id),
        "title": resource.title,
        "format": resource.format,
        "url": resource.url,
    }


@ns.route("/status/<dataset:dataset>/", endpoint="geopf_dataset_status")
class GeopfDatasetStatusAPI(API):
    @api.secure
    @api.doc("geopf_dataset_status")
    def get(self, dataset):
        """A dataset's Géoplateforme sync state, as stored locally.

        A pure read of the dataset's and its resources' `geopf:*` extras: no
        call to the geopf API and no token refresh, so it answers the same
        whether or not the current user is connected.

        Resources are split into those eligible for a push (format in
        `GEOPF_PUSHABLE_FORMATS`) and those that came back from a pull as
        offerings; the two are disjoint.

        A `status` of `null` means "never run"; otherwise it is one of
        `pending`, `done`, `error` or `timeout`.
        """
        # endpoint only returns public data
        dataset.permissions["read"].test()

        pushable_formats = current_app.config["GEOPF_PUSHABLE_FORMATS"]
        pushable = []
        offerings = []
        for resource in dataset.resources:
            extras = resource.extras
            offering_id = extras.get("geopf:offering:id")
            if offering_id:
                offerings.append(
                    {
                        **_resource_summary(resource),
                        "offering_id": offering_id,
                        "last_synced_at": extras.get("geopf:offering:last-synced-at"),
                    }
                )
            elif resource.format and resource.format.lower() in pushable_formats:
                pushable.append(
                    {
                        **_resource_summary(resource),
                        "push": {
                            "status": extras.get("geopf:push:status"),
                            "last_synced_at": extras.get("geopf:push:last-synced-at"),
                            "error": extras.get("geopf:push:error"),
                            "task_id": extras.get("geopf:push:task-id"),
                            "stored_data_id": extras.get("geopf:push:stored-data-id"),
                        },
                    }
                )

        return {
            "datastore_id": dataset.extras.get("geopf:push:datastore-id"),
            "fiche_url": dataset.extras.get("geopf:push:fiche-url"),
            "pull": {
                "status": dataset.extras.get("geopf:pull:status"),
                "last_synced_at": dataset.extras.get("geopf:pull:last-synced-at"),
                "error": dataset.extras.get("geopf:pull:error"),
                "task_id": dataset.extras.get("geopf:pull:task-id"),
            },
            "pushable": pushable,
            "offerings": offerings,
        }


@ns.route("/token/", endpoint="geopf_token")
class GeopfTokenAPI(API):
    @api.secure
    @api.doc("geopf_disconnect")
    def delete(self):
        """Disconnect the current user from Géoplateforme."""
        geopf_token = GeopfToken.objects(user=current_user.id).first()
        if geopf_token:
            revoke_token(geopf_token)
            geopf_token.delete()
        return "", 204


@ns.route("/datastores/", endpoint="geopf_datastores")
class GeopfDatastoresAPI(API):
    @api.secure
    @api.doc("geopf_datastores")
    def get(self):
        """List the entrepôts (datastores) available to the current user's geopf account."""
        try:
            access_token = resolve_access_token(user=current_user._get_current_object())
        except GeopfReauthRequired:
            api.abort(424, "Not connected to Géoplateforme")

        try:
            return GeopfClient(token=access_token).list_datastores()
        except GeopfError as e:
            api.abort(502, str(e))


@ns.route("/push/<dataset:dataset>/<uuid:rid>/", endpoint="geopf_push")
class GeopfPushAPI(API):
    @api.secure
    @api.doc("geopf_push")
    def post(self, dataset, rid):
        """Push a resource to Géoplateforme, as the current user."""
        dataset.permissions["edit_resources"].test()

        resource = get_by(dataset.resources, id=rid)
        if resource is None:
            api.abort(404, "Resource not found")
        pushable_formats = current_app.config["GEOPF_PUSHABLE_FORMATS"]
        if not resource.format or resource.format.lower() not in pushable_formats:
            api.abort(
                400,
                f"Only {', '.join(sorted(pushable_formats))} resources can be pushed to Géoplateforme",
            )

        user = current_user._get_current_object()
        try:
            resolve_access_token(user=user)
        except GeopfReauthRequired:
            api.abort(424, "Not connected to Géoplateforme")

        datastore_id = (request.get_json(silent=True) or {}).get("datastore_id")
        if not (datastore_id or dataset.extras.get("geopf:push:datastore-id")):
            api.abort(400, "No datastore_id provided and no datastore configured for this dataset")

        # Mark pending before enqueueing, so the status route doesn't read as
        # "never pushed" until a worker picks the task up. The id only exists
        # after `.delay()`, hence the second write.
        set_resource_extras(
            dataset, resource, {"geopf:push:status": "pending", "geopf:push:error": None}
        )
        task = push_resource_to_geopf.delay(
            str(dataset.id), str(resource.id), str(user.id), datastore_id
        )
        set_resource_extras(dataset, resource, {"geopf:push:task-id": task.id})
        return {"task_id": task.id}, 202


@ns.route("/pull-offerings/<dataset:dataset>/", endpoint="geopf_pull_offerings")
class GeopfPullOfferingsAPI(API):
    @api.secure
    @api.doc("geopf_pull_offerings")
    def post(self, dataset):
        """Pull Géoplateforme offerings into resources for this dataset, as the current user."""
        dataset.permissions["edit_resources"].test()

        user = current_user._get_current_object()
        try:
            resolve_access_token(user=user)
        except GeopfReauthRequired:
            api.abort(424, "Not connected to Géoplateforme")

        set_dataset_extras(dataset, {"geopf:pull:status": "pending", "geopf:pull:error": None})
        task = pull_offerings_from_geopf.delay(str(dataset.id), str(user.id))
        set_dataset_extras(dataset, {"geopf:pull:task-id": task.id})
        return {"task_id": task.id}, 202
