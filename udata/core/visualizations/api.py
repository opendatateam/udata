from datetime import datetime

from flask import request
from flask_login import current_user

from udata.api import API, api
from udata.api_fields import patch

from .models import Chart

ns = api.namespace("visualizations", "Visualizations related operations")

common_doc = {"params": {"visualization": "The visualization ID or slug"}}


@ns.route("/", endpoint="visualizations")
class VisualizationsAPI(API):
    """Visualizations collection endpoint"""

    @api.doc("list_visualizations")
    @api.expect(Chart.__index_parser__)
    @api.marshal_with(Chart.__page_fields__)
    def get(self):
        """List or search all visualizations"""
        query = Chart.objects(private__ne=True, deleted_at=None)

        return Chart.apply_pagination(Chart.apply_sort_filters(query))

    @api.secure
    @api.doc("create_visualization", responses={400: "Validation error"})
    @api.expect(Chart.__write_fields__)
    @api.marshal_with(Chart.__read_fields__, code=201)
    def post(self):
        """Create a new visualization"""
        visualization = patch(Chart(), request)
        if not visualization.owner and not visualization.organization:
            visualization.owner = current_user._get_current_object()
        visualization.save()
        return visualization, 201


@ns.route("/<visualization:visualization>/", endpoint="visualization", doc=common_doc)
class VisualizationAPI(API):
    @api.doc("get_visualization")
    @api.marshal_with(Chart.__read_fields__)
    def get(self, visualization):
        """Get a visualization given its identifier"""
        if not visualization.permissions["read"].can():
            if not visualization.private and visualization.deleted_at:
                api.abort(410, "Visualization has been deleted")
            api.abort(404)
        return visualization

    @api.secure
    @api.doc("update_visualization", responses={400: "Validation error"})
    @api.expect(Chart.__write_fields__)
    @api.marshal_with(Chart.__read_fields__)
    def patch(self, visualization):
        """Update a visualization given its identifier"""
        if visualization.deleted_at:
            api.abort(410, "Visualization has been deleted")

        visualization.permissions["edit"].test()

        patch(visualization, request)
        visualization.save()
        return visualization

    @api.secure
    @api.doc("delete_visualization")
    @api.response(204, "Visualization deleted")
    def delete(self, visualization):
        """Delete a visualization given its identifier"""
        if visualization.deleted_at:
            api.abort(410, "Visualization has been deleted")

        visualization.permissions["delete"].test()

        visualization.deleted_at = datetime.utcnow()
        visualization.save()
        return "", 204
