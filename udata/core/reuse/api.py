from datetime import datetime
from typing import List

import mongoengine
from bson.objectid import ObjectId
from feedgenerator.django.utils.feedgenerator import Atom1Feed
from flask import make_response, request
from flask_login import current_user

from udata.api import API, api, errors
from udata.api.parsers import ModelApiParser
from udata.api_fields import patch, patch_and_save
from udata.auth import admin_permission
from udata.core.badges import api as badges_api
from udata.core.badges.fields import badge_fields
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.core.followers.api import FollowAPI
from udata.core.organization.models import Organization
from udata.core.reuse.constants import REUSE_TOPICS, REUSE_TYPES
from udata.core.storages.api import (
    image_parser,
    parse_uploaded_image,
    uploaded_image_fields,
)
from udata.frontend.markdown import md
from udata.i18n import gettext as _
from udata.models import Dataset
from udata.utils import id_or_404

from .api_fields import (
    reuse_suggestion_fields,
    reuse_topic_fields,
    reuse_type_fields,
)
from .models import Reuse

DEFAULT_SORTING = "-created_at"
SUGGEST_SORTING = "-metrics.followers"


class ReuseApiParser(ModelApiParser):
    sorts = {
        "title": "title",
        "created": "created_at",
        "last_modified": "last_modified",
        "datasets": "metrics.datasets",
        "followers": "metrics.followers",
        "views": "metrics.views",
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument("dataset", type=str, location="args")
        self.parser.add_argument("tag", type=str, location="args")
        self.parser.add_argument("organization", type=str, location="args")
        self.parser.add_argument(
            "organization_badge",
            type=str,
            choices=list(Organization.__badges__),
            location="args",
        )
        self.parser.add_argument("owner", type=str, location="args")
        self.parser.add_argument("type", type=str, location="args")
        self.parser.add_argument("topic", type=str, location="args")
        self.parser.add_argument("featured", type=bool, location="args")

    @staticmethod
    def parse_filters(reuses, args):
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            reuses = reuses.search_text(phrase_query)
        if args.get("dataset"):
            if not ObjectId.is_valid(args["dataset"]):
                api.abort(400, "Dataset arg must be an identifier")
            reuses = reuses.filter(datasets=args["dataset"])
        if args.get("featured"):
            reuses = reuses.filter(featured=args["featured"])
        if args.get("topic"):
            reuses = reuses.filter(topic=args["topic"])
        if args.get("type"):
            reuses = reuses.filter(type=args["type"])
        if args.get("tag"):
            reuses = reuses.filter(tags=args["tag"])
        if args.get("organization"):
            if not ObjectId.is_valid(args["organization"]):
                api.abort(400, "Organization arg must be an identifier")
            reuses = reuses.filter(organization=args["organization"])
        if args.get("organization_badge"):
            orgs = Organization.objects.with_badge(args["organization_badge"])
            reuses = reuses.filter(organization__in=orgs)
        if args.get("owner"):
            if not ObjectId.is_valid(args["owner"]):
                api.abort(400, "Owner arg must be an identifier")
            reuses = reuses.filter(owner=args["owner"])
        return reuses


ns = api.namespace("reuses", "Reuse related operations")

common_doc = {"params": {"reuse": "The reuse ID or slug"}}

reuse_parser = ReuseApiParser()


@ns.route("/", endpoint="reuses")
class ReuseListAPI(API):
    @api.doc("list_reuses")
    @api.expect(Reuse.__index_parser__)
    @api.marshal_with(Reuse.__page_fields__)
    def get(self):
        query = Reuse.objects.visible_by_user(
            current_user, mongoengine.Q(private__ne=True, deleted=None)
        )
        return Reuse.apply_pagination(Reuse.apply_sort_filters(query))

    @api.secure
    @api.doc("create_reuse")
    @api.expect(Reuse.__write_fields__)
    @api.response(400, "Validation error")
    @api.marshal_with(Reuse.__read_fields__, code=201)
    def post(self):
        reuse = patch(Reuse(), request)

        if not reuse.owner and not reuse.organization:
            reuse.owner = current_user._get_current_object()

        reuse.save()

        return patch_and_save(reuse, request), 201


@ns.route("/recent.atom", endpoint="recent_reuses_atom_feed")
class ReusesAtomFeedAPI(API):
    @api.doc("recent_reuses_atom_feed")
    def get(self):
        feed = Atom1Feed(
            _("Latests reuses"),
            description=None,
            feed_url=request.url,
            link=request.url_root,
        )

        reuses: List[Reuse] = Reuse.objects.visible().order_by("-created_at").limit(15)
        for reuse in reuses:
            author_name = None
            author_uri = None
            if reuse.organization:
                author_name = reuse.organization.name
                author_uri = reuse.organization.url_for()
            elif reuse.owner:
                author_name = reuse.owner.fullname
                author_uri = reuse.owner.url_for()
            feed.add_item(
                reuse.title,
                unique_id=reuse.id,
                description=reuse.description,
                content=md(reuse.description),
                author_name=author_name,
                author_link=author_uri,
                link=reuse.url_for(),
                updateddate=reuse.last_modified,
                pubdate=reuse.created_at,
            )
        response = make_response(feed.writeString("utf-8"))
        response.headers["Content-Type"] = "application/atom+xml"
        return response


@ns.route("/<reuse:reuse>/", endpoint="reuse", doc=common_doc)
@api.response(404, "Reuse not found")
@api.response(410, "Reuse has been deleted")
class ReuseAPI(API):
    @api.doc("get_reuse")
    @api.marshal_with(Reuse.__read_fields__)
    def get(self, reuse):
        """Fetch a given reuse"""
        if not reuse.permissions["edit"].can():
            if reuse.private:
                api.abort(404)
            elif reuse.deleted:
                api.abort(410, "This reuse has been deleted")
        return reuse

    @api.secure
    @api.doc("update_reuse")
    @api.expect(Reuse.__write_fields__)
    @api.marshal_with(Reuse.__read_fields__)
    @api.response(400, errors.VALIDATION_ERROR)
    def put(self, reuse):
        """Update a given reuse"""
        request_deleted = request.json.get("deleted", True)
        if reuse.deleted and request_deleted is not None:
            api.abort(410, "This reuse has been deleted")
        reuse.permissions["edit"].test()

        # This is a patch but old API acted like PATCH on PUT requests.
        return patch_and_save(reuse, request)

    @api.secure
    @api.doc("delete_reuse")
    @api.response(204, "Reuse deleted")
    def delete(self, reuse):
        """Delete a given reuse"""
        if reuse.deleted:
            api.abort(410, "This reuse has been deleted")
        reuse.permissions["delete"].test()
        reuse.deleted = datetime.utcnow()
        reuse.save()
        return "", 204


@ns.route("/<reuse:reuse>/datasets/", endpoint="reuse_add_dataset")
class ReuseDatasetsAPI(API):
    @api.secure
    @api.doc("reuse_add_dataset", **common_doc)
    @api.expect(dataset_ref_fields)
    @api.response(200, "The dataset is already present", Reuse.__read_fields__)
    @api.marshal_with(Reuse.__read_fields__, code=201)
    def post(self, reuse):
        """Add a dataset to a given reuse"""
        if "id" not in request.json:
            api.abort(400, "Expect a dataset identifier")
        try:
            dataset = Dataset.objects.get_or_404(id=id_or_404(request.json["id"]))
        except Dataset.DoesNotExist:
            msg = "Dataset {0} does not exists".format(request.json["id"])
            api.abort(404, msg)
        if dataset in reuse.datasets:
            return reuse
        reuse.datasets.append(dataset)
        reuse.save()
        return reuse, 201


@ns.route("/badges/", endpoint="available_reuse_badges")
class AvailableDatasetBadgesAPI(API):
    @api.doc("available_reuse_badges")
    def get(self):
        """List all available reuse badges and their labels"""
        return Reuse.__badges__


@ns.route("/<reuse:reuse>/badges/", endpoint="reuse_badges")
class ReuseBadgesAPI(API):
    @api.doc("add_reuse_badge", **common_doc)
    @api.expect(badge_fields)
    @api.marshal_with(badge_fields)
    @api.secure(admin_permission)
    def post(self, reuse):
        """Create a new badge for a given reuse"""
        return badges_api.add(reuse)


@ns.route("/<reuse:reuse>/badges/<badge_kind>/", endpoint="reuse_badge")
class ReuseBadgeAPI(API):
    @api.doc("delete_reuse_badge", **common_doc)
    @api.secure(admin_permission)
    def delete(self, reuse, badge_kind):
        """Delete a badge for a given reuse"""
        return badges_api.remove(reuse, badge_kind)


@ns.route("/<reuse:reuse>/featured/", endpoint="reuse_featured")
@api.doc(**common_doc)
class ReuseFeaturedAPI(API):
    @api.doc("feature_reuse")
    @api.secure(admin_permission)
    @api.marshal_with(Reuse.__read_fields__)
    def post(self, reuse):
        """Mark a reuse as featured"""
        reuse.featured = True
        reuse.save()
        return reuse

    @api.doc("unfeature_reuse")
    @api.secure(admin_permission)
    @api.marshal_with(Reuse.__read_fields__)
    def delete(self, reuse):
        """Unmark a reuse as featured"""
        reuse.featured = False
        reuse.save()
        return reuse


@ns.route("/<id>/followers/", endpoint="reuse_followers")
@ns.doc(
    get={"id": "list_reuse_followers"}, post={"id": "follow_reuse"}, delete={"id": "unfollow_reuse"}
)
class FollowReuseAPI(FollowAPI):
    model = Reuse


suggest_parser = api.parser()
suggest_parser.add_argument(
    "q", help="The string to autocomplete/suggest", location="args", required=True
)
suggest_parser.add_argument(
    "size", type=int, help="The amount of suggestion to fetch", location="args", default=10
)


@ns.route("/suggest/", endpoint="suggest_reuses")
class ReusesSuggestAPI(API):
    @api.doc("suggest_reuses")
    @api.expect(suggest_parser)
    @api.marshal_list_with(reuse_suggestion_fields)
    def get(self):
        """Reuses suggest endpoint using mongoDB contains"""
        args = suggest_parser.parse_args()
        reuses = Reuse.objects(
            archived=None, deleted=None, private__ne=True, title__icontains=args["q"]
        )
        return [
            {
                "id": reuse.id,
                "title": reuse.title,
                "slug": reuse.slug,
                "image_url": reuse.image,
                "page": reuse.self_web_url(),
            }
            for reuse in reuses.order_by(SUGGEST_SORTING).limit(args["size"])
        ]


@ns.route("/<reuse:reuse>/image/", endpoint="reuse_image")
@api.doc(**common_doc)
class ReuseImageAPI(API):
    @api.secure
    @api.doc("reuse_image")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def post(self, reuse):
        """Upload a new reuse image"""
        reuse.permissions["edit"].test()
        parse_uploaded_image(reuse.image)
        reuse.save()

        return reuse


@ns.route("/types/", endpoint="reuse_types")
class ReuseTypesAPI(API):
    @api.doc("reuse_types")
    @api.marshal_list_with(reuse_type_fields)
    def get(self):
        """List all reuse types"""
        return [{"id": id, "label": label} for id, label in REUSE_TYPES.items()]


@ns.route("/topics/", endpoint="reuse_topics")
class ReuseTopicsAPI(API):
    @api.doc("reuse_topics")
    @api.marshal_list_with(reuse_topic_fields)
    def get(self):
        """List all reuse topics"""
        return [{"id": id, "label": label} for id, label in REUSE_TOPICS.items()]
