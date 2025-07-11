from datetime import datetime
from typing import List

from feedgenerator.django.utils.feedgenerator import Atom1Feed
from flask import make_response, request

from udata.api import API, api, fields
from udata.auth import Permission as AdminPermission
from udata.auth import admin_permission
from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.models import Reuse
from udata.core.storages.api import (
    image_parser,
    parse_uploaded_image,
    uploaded_image_fields,
)
from udata.core.user.api_fields import user_ref_fields
from udata.frontend.markdown import md
from udata.i18n import gettext as _

from .forms import PostForm
from .models import Post

DEFAULT_SORTING = "-published"

ns = api.namespace("posts", "Posts related operations")

post_fields = api.model(
    "Post",
    {
        "id": fields.String(description="The post identifier"),
        "name": fields.String(description="The post name", required=True),
        "slug": fields.String(description="The post permalink string", readonly=True),
        "headline": fields.String(description="The post headline", required=True),
        "content": fields.Markdown(description="The post content in Markdown", required=True),
        "image": fields.ImageField(description="The post image", readonly=True),
        "credit_to": fields.String(description="An optional credit line (associated to the image)"),
        "credit_url": fields.String(description="An optional link associated to the credits"),
        "tags": fields.List(fields.String, description="Some keywords to help in search"),
        "datasets": fields.List(fields.Nested(dataset_fields), description="The post datasets"),
        "reuses": fields.List(fields.Nested(Reuse.__read_fields__), description="The post reuses"),
        "owner": fields.Nested(
            user_ref_fields, description="The owner user", readonly=True, allow_null=True
        ),
        "created_at": fields.ISODateTime(description="The post creation date", readonly=True),
        "last_modified": fields.ISODateTime(
            description="The post last modification date", readonly=True
        ),
        "published": fields.ISODateTime(description="The post publication date", readonly=True),
        "body_type": fields.String(description="HTML or markdown body type", default="markdown"),
        "uri": fields.String(
            attribute=lambda p: p.self_api_url(),
            description="The API URI for this post",
            readonly=True,
        ),
        "page": fields.String(
            attribute=lambda p: p.self_web_url(),
            description="The post web page URL",
            readonly=True,
        ),
    },
    mask="*,datasets{id,title,acronym,uri,page},reuses{id,title,image,image_thumbnail,uri,page}",
)

post_page_fields = api.model("PostPage", fields.pager(post_fields))

parser = api.page_parser()

parser.add_argument("sort", type=str, location="args", help="The sorting attribute")
parser.add_argument(
    "with_drafts",
    type=bool,
    default=False,
    location="args",
    help="`True` also returns the unpublished posts (only for super-admins)",
)
parser.add_argument(
    "q", type=str, location="args", help="query string to search through resources titles"
)


@ns.route("/", endpoint="posts")
class PostsAPI(API):
    @api.doc("list_posts")
    @api.expect(parser)
    @api.marshal_with(post_page_fields)
    def get(self):
        """List all posts"""
        args = parser.parse_args()

        posts = Post.objects()

        if not (AdminPermission().can() and args["with_drafts"]):
            posts = posts.published()

        if args["q"]:
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            posts = posts.search_text(phrase_query)

        sort = args["sort"] or ("$text_score" if args["q"] else None) or DEFAULT_SORTING
        return posts.order_by(sort).paginate(args["page"], args["page_size"])

    @api.doc("create_post")
    @api.secure(admin_permission)
    @api.expect(post_fields)
    @api.marshal_with(post_fields)
    @api.response(400, "Validation error")
    def post(self):
        """Create a post"""
        form = api.validate(PostForm)
        return form.save(), 201


@ns.route("/recent.atom", endpoint="recent_posts_atom_feed")
class PostsAtomFeedAPI(API):
    @api.doc("recent_posts_atom_feed")
    def get(self):
        feed = Atom1Feed(
            _("Latests posts"),
            description=None,
            feed_url=request.url,
            link=request.url_root,
        )

        posts: List[Post] = Post.objects().published().order_by("-published").limit(15)
        for post in posts:
            feed.add_item(
                post.name,
                unique_id=post.id,
                description=post.headline,
                content=md(post.content),
                author_name="data.gouv.fr",
                link=post.url_for(),
                updateddate=post.last_modified,
                pubdate=post.published,
            )
        response = make_response(feed.writeString("utf-8"))
        response.headers["Content-Type"] = "application/atom+xml"
        return response


@ns.route("/<post:post>/", endpoint="post")
@api.response(404, "Object not found")
@api.param("post", "The post ID or slug")
class PostAPI(API):
    @api.doc("get_post")
    @api.marshal_with(post_fields)
    def get(self, post):
        """Get a given post"""
        return post

    @api.doc("update_post")
    @api.secure(admin_permission)
    @api.expect(post_fields)
    @api.marshal_with(post_fields)
    @api.response(400, "Validation error")
    def put(self, post):
        """Update a given post"""
        form = api.validate(PostForm, post)
        return form.save()

    @api.secure(admin_permission)
    @api.doc("delete_post")
    @api.response(204, "Object deleted")
    def delete(self, post):
        """Delete a given post"""
        post.delete()
        return "", 204


@ns.route("/<post:post>/publish", endpoint="publish_post")
class PublishPostAPI(API):
    @api.secure(admin_permission)
    @api.doc("publish_post")
    @api.marshal_with(post_fields)
    def post(self, post):
        """Publish an existing post"""
        post.modify(published=datetime.utcnow())
        return post

    @api.secure(admin_permission)
    @api.doc("unpublish_post")
    @api.marshal_with(post_fields)
    def delete(self, post):
        """Publish an existing post"""
        post.modify(published=None)
        return post


@ns.route("/<post:post>/image/", endpoint="post_image")
class PostImageAPI(API):
    @api.secure(admin_permission)
    @api.doc("post_image")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def post(self, post):
        """Upload a new image"""
        parse_uploaded_image(post.image)
        post.save()
        return post

    @api.secure(admin_permission)
    @api.doc("resize_post_image")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def put(self, post):
        """Set the image BBox"""
        parse_uploaded_image(post.image)
        return post
