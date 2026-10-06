from datetime import UTC, datetime

from flask import request
from flask_login import current_user
from mongoengine import Q

from udata.api import API, api, errors
from udata.api_fields import patch, patch_and_save

from .models import Page

ns = api.namespace("pages", "Pages related operations")


@ns.route("/", endpoint="pages")
class PagesAPI(API):
    @api.doc("list_pages")
    @api.expect(Page.__index_parser__)
    @api.marshal_with(Page.__page_fields__)
    def get(self):
        """List all pages visible to the current user"""
        pages = Page.objects.visible_by_user(current_user, Q(published__ne=None))
        return Page.apply_pagination(Page.apply_sort_filters(pages))

    @api.secure
    @api.doc("create_page")
    @api.expect(Page.__write_fields__)
    @api.response(400, errors.VALIDATION_ERROR)
    @api.marshal_with(Page.__read_fields__, code=201)
    def post(self):
        """Create a page"""
        page = patch(Page(), request)

        if not page.owner and not page.organization:
            page.owner = current_user._get_current_object()

        page.save()
        return page, 201


@ns.route("/<page:page>/", endpoint="page")
@api.param("page", "The page ID or slug")
@api.response(404, "Object not found")
class PageAPI(API):
    @api.doc("get_page")
    @api.marshal_with(Page.__read_fields__)
    def get(self, page):
        """Get a given page"""
        if not page.permissions["read"].can():
            api.abort(404)
        return page

    @api.secure
    @api.doc("update_page")
    @api.expect(Page.__write_fields__)
    @api.response(400, errors.VALIDATION_ERROR)
    @api.marshal_with(Page.__read_fields__)
    def put(self, page):
        """Update a given page"""
        page.permissions["edit"].test()
        return patch_and_save(page, request)

    @api.secure
    @api.doc("delete_page")
    @api.response(204, "Object deleted")
    def delete(self, page):
        """Delete a given page"""
        page.permissions["delete"].test()
        page.delete()
        return "", 204


@ns.route("/<page:page>/publish/", endpoint="publish_page")
@api.param("page", "The page ID or slug")
class PublishPageAPI(API):
    @api.secure
    @api.doc("publish_page")
    @api.marshal_with(Page.__read_fields__)
    def post(self, page):
        """Publish a page"""
        page.permissions["edit"].test()
        if not page.is_visible:
            page.published = datetime.now(UTC)
            page.save()
        return page

    @api.secure
    @api.doc("unpublish_page")
    @api.marshal_with(Page.__read_fields__)
    def delete(self, page):
        """Unpublish a page"""
        page.permissions["edit"].test()
        page.published = None
        page.save()
        return page
