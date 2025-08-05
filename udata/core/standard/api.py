from datetime import datetime

from flask import request
from flask_login import current_user

from udata.api import API, api, errors
from udata.api_fields import patch, patch_and_save

from .models import Standard
from .permissions import StandardEditPermission

ns = api.namespace("standards", "Standards related operations")

common_doc = {"params": {"standard": "The standard ID or slug"}}


@ns.route("/", endpoint="standards")
class StandardListAPI(API):
    @api.doc("list_standards")
    @api.expect(Standard.__index_parser__)
    @api.marshal_with(Standard.__page_fields__)
    def get(self):
        query = Standard.objects(deleted=None)
        return Standard.apply_pagination(Standard.apply_sort_filters(query))

    @api.secure
    @api.doc("create_standard")
    @api.expect(Standard.__write_fields__)
    @api.response(400, "Validation error")
    @api.marshal_with(Standard.__read_fields__, code=201)
    def post(self):
        standard = patch(Standard(), request)

        if not standard.owner and not standard.organization:
            standard.owner = current_user._get_current_object()

        standard.save()

        return patch_and_save(standard, request), 201


@ns.route("/<standard:standard>/", endpoint="standard", doc=common_doc)
class StandardAPI(API):
    @api.doc("get_standard")
    @api.marshal_with(Standard.__read_fields__)
    def get(self, standard):
        """Fetch a given standard"""
        if not StandardEditPermission(standard).can():
            if standard.private:
                api.abort(404)
            elif standard.deleted:
                api.abort(410, "This standard has been deleted")
        return standard

    @api.secure
    @api.doc("update_standard")
    @api.expect(Standard.__write_fields__)
    @api.marshal_with(Standard.__read_fields__)
    @api.response(400, errors.VALIDATION_ERROR)
    def put(self, standard):
        """Update a given standard"""
        request_deleted = request.json.get("deleted", True)
        if standard.deleted and request_deleted is not None:
            api.abort(410, "This standard has been deleted")
        StandardEditPermission(standard).test()

        # This is a patch but old API acted like PATCH on PUT requests.
        return patch_and_save(standard, request)

    @api.secure
    @api.doc("delete_standard")
    @api.response(204, "Standard deleted")
    def delete(self, standard):
        """Delete a given standard"""
        if standard.deleted:
            api.abort(410, "This standard has been deleted")
        StandardEditPermission(standard).test()
        standard.deleted = datetime.utcnow()
        standard.save()
        return "", 204
