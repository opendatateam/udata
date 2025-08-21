from flask import request
from flask_login import current_user

from udata.api import API, api
from udata.api_fields import patch
from udata.auth import admin_permission

from .models import Page

ns = api.namespace("pages", "Pages related operations (beta)")

common_doc = {"params": {"page": "The page ID or slug"}}


@ns.route("/", endpoint="pages")
class PagesAPI(API):
    @api.secure(admin_permission)
    @api.doc("list_pages")
    @api.expect(Page.__index_parser__)
    @api.marshal_with(Page.__page_fields__)
    def get(self):
        """List or search all pages"""
        return Page.apply_pagination(Page.objects)

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


@ns.route("/<page:page>/", endpoint="page")
class PageAPI(API):
    @api.doc("get_page")
    @api.marshal_with(Page.__read_fields__)
    def get(self, page: Page):
        return page

    @api.secure
    @api.doc("update_page")
    @api.expect(Page.__write_fields__)
    @api.marshal_with(Page.__read_fields__)
    def put(self, page: Page):
        page.permissions["edit"].test()
        patch(page, request)

        page.save()
        return page
