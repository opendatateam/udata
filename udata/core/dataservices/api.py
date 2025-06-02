from datetime import datetime
from typing import List

import mongoengine
from bson import ObjectId
from feedgenerator.django.utils.feedgenerator import Atom1Feed
from flask import make_response, redirect, request, url_for
from flask_login import current_user

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.core.dataservices.permissions import OwnablePermission
from udata.core.dataset.models import Dataset
from udata.core.followers.api import FollowAPI
from udata.core.site.models import current_site
from udata.frontend.markdown import md
from udata.i18n import gettext as _
from udata.rdf import RDF_EXTENSIONS, graph_response, negociate_content

from .models import Dataservice
from .permissions import DataserviceEditPermission
from .rdf import dataservice_to_rdf

ns = api.namespace("dataservices", "Dataservices related operations (beta)")

common_doc = {"params": {"dataservice": "The dataservice ID or slug"}}


@ns.route("/", endpoint="dataservices")
class DataservicesAPI(API):
    """Dataservices collection endpoint"""

    @api.doc("list_dataservices")
    @api.expect(Dataservice.__index_parser__)
    @api.marshal_with(Dataservice.__page_fields__)
    def get(self):
        """List or search all dataservices"""
        query = Dataservice.objects.visible_by_user(
            current_user, mongoengine.Q(private__ne=True, archived_at=None, deleted_at=None)
        )

        return Dataservice.apply_pagination(Dataservice.apply_sort_filters(query))

    @api.secure
    @api.doc("create_dataservice", responses={400: "Validation error"})
    @api.expect(Dataservice.__write_fields__)
    @api.marshal_with(Dataservice.__read_fields__, code=201)
    def post(self):
        dataservice = patch(Dataservice(), request)
        if not dataservice.owner and not dataservice.organization:
            dataservice.owner = current_user._get_current_object()

        dataservice.save()
        return dataservice, 201


@ns.route("/recent.atom", endpoint="recent_dataservices_atom_feed")
class DataservicesAtomFeedAPI(API):
    @api.doc("recent_dataservices_atom_feed")
    def get(self):
        feed = Atom1Feed(
            _("Latest APIs"), description=None, feed_url=request.url, link=request.url_root
        )

        dataservices: List[Dataservice] = (
            Dataservice.objects.visible()
            .order_by("-created_at_internal")
            .limit(current_site.feed_size)
        )
        for dataservice in dataservices:
            author_name = None
            author_uri = None
            if dataservice.organization:
                author_name = dataservice.organization.name
                author_uri = dataservice.organization.external_url
            elif dataservice.owner:
                author_name = dataservice.owner.fullname
                author_uri = dataservice.owner.external_url
            feed.add_item(
                dataservice.title,
                unique_id=dataservice.id,
                description=dataservice.description,
                content=md(dataservice.description),
                author_name=author_name,
                author_link=author_uri,
                link=dataservice.url_for(external=True),
                updateddate=dataservice.metadata_modified_at,
                pubdate=dataservice.created_at,
            )
        response = make_response(feed.writeString("utf-8"))
        response.headers["Content-Type"] = "application/atom+xml"
        return response


@ns.route("/<dataservice:dataservice>/", endpoint="dataservice")
class DataserviceAPI(API):
    @api.doc("get_dataservice")
    @api.marshal_with(Dataservice.__read_fields__)
    def get(self, dataservice):
        if not OwnablePermission(dataservice).can():
            if dataservice.private:
                api.abort(404)
            elif dataservice.deleted_at:
                api.abort(410, "Dataservice has been deleted")
        return dataservice

    @api.secure
    @api.doc("update_dataservice", responses={400: "Validation error"})
    @api.expect(Dataservice.__write_fields__)
    @api.marshal_with(Dataservice.__read_fields__)
    def patch(self, dataservice):
        if dataservice.deleted_at and not (
            # Allow requests containing "deleted_at: None" to undelete.
            "deleted_at" in request.json and request.json.get("deleted_at") is None
        ):
            api.abort(410, "dataservice has been deleted")

        OwnablePermission(dataservice).test()

        patch(dataservice, request)
        dataservice.metadata_modified_at = datetime.utcnow()

        dataservice.save()
        return dataservice

    @api.secure
    @api.doc("delete_dataservice")
    @api.response(204, "dataservice deleted")
    def delete(self, dataservice):
        if dataservice.deleted_at:
            api.abort(410, "dataservice has been deleted")

        OwnablePermission(dataservice).test()
        dataservice.deleted_at = datetime.utcnow()
        dataservice.metadata_modified_at = datetime.utcnow()
        dataservice.save()

        return "", 204


dataservice_add_datasets_fields = api.model(
    "DataserviceDatasetsAdd",
    {
        "id": fields.String(description="Id of the dataset to add", required=True),
    },
    location="json",
)


@ns.route("/<dataservice:dataservice>/datasets/", endpoint="dataservice_datasets", doc=common_doc)
class DataserviceDatasetsAPI(API):
    @api.secure
    @api.doc("dataservice_datasets_create")
    @api.expect([dataservice_add_datasets_fields])
    @api.marshal_with(Dataservice.__read_fields__)
    @api.response(400, "Malformed object id(s) in request")
    @api.response(400, "Expecting a list")
    @api.response(400, "Expecting a list of dicts with id attribute")
    @api.response(404, "Dataservice not found")
    @api.response(403, "Forbidden")
    @api.response(410, "Dataservice has been deleted")
    def post(self, dataservice):
        if dataservice.deleted_at:
            api.abort(410, "Dataservice has been deleted")

        OwnablePermission(dataservice).test()

        data = request.json

        if not isinstance(data, list):
            api.abort(400, "Expecting a list")
        if not all(isinstance(d, dict) and d.get("id") for d in data):
            api.abort(400, "Expecting a list of dicts with id attribute")

        try:
            datasets = Dataset.objects.filter(id__in=[d["id"] for d in data]).only("id")
            diff = set(d.id for d in datasets) - set(d.id for d in dataservice.datasets)
        except mongoengine.errors.ValidationError:
            api.abort(400, "Malformed object id(s) in request")

        if diff:
            dataservice.datasets += [ObjectId(did) for did in diff]
            dataservice.metadata_modified_at = datetime.utcnow()
            dataservice.save()

        return dataservice, 201


@ns.route(
    "/<dataservice:dataservice>/datasets/<dataset:dataset>/",
    endpoint="dataservice_dataset",
    doc=common_doc,
)
class DataserviceDatasetAPI(API):
    @api.secure
    @api.response(404, "Dataservice not found")
    @api.response(404, "Dataset not found in dataservice")
    def delete(self, dataservice, dataset):
        if dataservice.deleted_at:
            api.abort(410, "Dataservice has been deleted")

        OwnablePermission(dataservice).test()

        if dataset not in dataservice.datasets:
            api.abort(404, "Dataset not found in dataservice")
        dataservice.datasets = [d for d in dataservice.datasets if d.id != dataset.id]
        dataservice.metadata_modified_at = datetime.utcnow()
        dataservice.save()

        return None, 204


@ns.route("/<dataservice:dataservice>/rdf", endpoint="dataservice_rdf", doc=common_doc)
@api.response(404, "Dataservice not found")
@api.response(410, "Dataservice has been deleted")
class DataserviceRdfAPI(API):
    @api.doc("rdf_dataservice")
    def get(self, dataservice):
        format = RDF_EXTENSIONS[negociate_content()]
        url = url_for("api.dataservice_rdf_format", dataservice=dataservice.id, format=format)
        return redirect(url)


@ns.route(
    "/<dataservice:dataservice>/rdf.<format>", endpoint="dataservice_rdf_format", doc=common_doc
)
@api.response(404, "Dataservice not found")
@api.response(410, "Dataservice has been deleted")
class DataserviceRdfFormatAPI(API):
    @api.doc("rdf_dataservice_format")
    def get(self, dataservice, format):
        if not DataserviceEditPermission(dataservice).can():
            if dataservice.private:
                api.abort(404)
            elif dataservice.deleted_at:
                api.abort(410)

        resource = dataservice_to_rdf(dataservice)
        # bypass flask-restplus make_response, since graph_response
        # is handling the content negociation directly
        return make_response(*graph_response(resource, format))


@ns.route("/<id>/followers/", endpoint="dataservice_followers")
@ns.doc(
    get={"id": "list_dataservice_followers"},
    post={"id": "follow_dataservice"},
    delete={"id": "unfollow_dataservice"},
)
class DataserviceFollowersAPI(FollowAPI):
    model = Dataservice
