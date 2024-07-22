import flask_storage as fs
from flask import Blueprint, jsonify
from flask_security import login_required

from .api import UploadStatus, handle_upload, on_upload_status

blueprint = Blueprint("storage", __name__)


@blueprint.app_errorhandler(UploadStatus)
def jsonify_upload_status(status):
    payload, status = on_upload_status(status)
    return jsonify(payload), status


@login_required
@blueprint.route("/upload/<name>/", methods=["POST"])
def upload(name):
    """Handle upload on POST if authorized."""
    storage = fs.by_name(name)
    return jsonify(success=True, **handle_upload(storage))
