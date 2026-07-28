import mongoengine
from flask import current_app, redirect, request, session, url_for

from udata.api import API, api
from udata.auth import current_user
from udata.core.dataset.models import Dataset
from udata.uris import homepage_url
from udata.utils import get_by

from .auth import oauth, resolve_access_token, store_token
from .client import GeopfClient, GeopfError, GeopfReauthRequired
from .models import GeopfToken
from .tasks import pull_offerings_from_geopf, push_resource_to_geopf

ns = api.namespace("geopf", "Géoplateforme related operations")

DATASET_SESSION_KEY = "geopf_oauth_dataset_id"


def _redirect_target(dataset_id):
    """Resolve a dataset id to its cdata page, falling back to the homepage.

    We only ever accept an *id* from the client here, never a path or URL:
    it's resolved to a URL entirely server-side via `Dataset.self_web_url()`,
    so there is no open-redirect surface.
    """
    if dataset_id:
        try:
            url = Dataset.objects.get(id=dataset_id).self_web_url(flash="connected")
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
        """Whether the current user has an active geopf link."""
        geopf_token = GeopfToken.objects(user=current_user.id).first()
        if geopf_token is None:
            return {"connected": False, "expires_at": None}
        return {"connected": True, "expires_at": geopf_token.expires_at.isoformat()}


@ns.route("/token/", endpoint="geopf_token")
class GeopfTokenAPI(API):
    @api.secure
    @api.doc("geopf_disconnect")
    def delete(self):
        """Disconnect the current user from Géoplateforme."""
        GeopfToken.objects(user=current_user.id).delete()
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
            api.abort(409, "Not connected to Géoplateforme")

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
            api.abort(409, "Not connected to Géoplateforme")

        datastore_id = (request.get_json(silent=True) or {}).get("datastore_id")
        task = push_resource_to_geopf.delay(
            str(dataset.id), str(resource.id), str(user.id), datastore_id
        )
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
            api.abort(409, "Not connected to Géoplateforme")

        task = pull_offerings_from_geopf.delay(str(dataset.id), str(user.id))
        return {"task_id": task.id}, 202
