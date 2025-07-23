from flask import request
from flask_login import current_user

from udata.api import API, api
from udata.api_fields import patch

from .models import Page

ns = api.namespace("pages", "Pages related operations (beta)")

common_doc = {"params": {"page": "The page ID or slug"}}


@ns.route("/", endpoint="pages")
class PagesAPI(API):
    # @api.doc("list_pages")
    # @api.expect(P.__index_parser__)
    # @api.marshal_with(P.__page_fields__)
    # def get(self):
    #     """List or search all dataservices"""
    #     query = Dataservice.objects.visible_by_user(
    #         current_user, mongoengine.Q(private__ne=True, archived_at=None, deleted_at=None)
    #     )

    #     return Dataservice.apply_pagination(Dataservice.apply_sort_filters(query))

    @api.secure
    @api.doc("create_page", responses={400: "Validation error"})
    @api.expect(Page.__write_fields__)
    @api.marshal_with(Page.__read_fields__, code=201)
    def post(self):
        page = patch(Page(), request)
        if not page.owner and not page.organization:
            page.owner = current_user._get_current_object()

        page.save()
        return page, 201
