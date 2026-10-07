from datetime import UTC, datetime

from feedgenerator.django.utils.feedgenerator import Atom1Feed
from flask import make_response, request
from flask_login import current_user
from mongoengine import Q

from udata.api import API, api
from udata.api_fields import patch, patch_and_save
from udata.core.storages.api import (
    image_parser,
    parse_uploaded_image,
    uploaded_image_fields,
)
from udata.frontend.markdown import md
from udata.i18n import gettext as _

from .constants import EXTERNAL_PAGE
from .models import Post

DEFAULT_SORTING = "-published"

ns = api.namespace("posts", "Posts related operations")

parser = Post.__index_parser__
parser.add_argument(
    "with_drafts",
    type=bool,
    default=False,
    location="args",
    help="`True` also returns the unpublished posts you can read (yours, or all of them for super-admins)",
)


@ns.route("/", endpoint="posts")
class PostsAPI(API):
    @api.doc("list_posts")
    @api.expect(parser)
    @api.marshal_with(Post.__page_fields__)
    def get(self):
        """List all posts"""
        args = parser.parse_args()

        posts = Post.objects().visible()
        if args["with_drafts"]:
            posts = Post.objects.visible_by_user(current_user, Q(published__ne=None))

        if not (args.get("kind") or args.get("topic")):
            # External pages are only listed when asked for, they belong to other sites
            posts = posts.filter(kind__ne=EXTERNAL_PAGE)

        # The search is already handled by apply_sort_filters if searchable=True
        return Post.apply_pagination(Post.apply_sort_filters(posts))

    @api.secure
    @api.doc("create_post")
    @api.expect(Post.__write_fields__)
    @api.marshal_with(Post.__read_fields__)
    @api.response(400, "Validation error")
    def post(self):
        """Create a post"""
        post = patch(Post(), request)

        if not post.owner and not post.organization:
            post.owner = current_user._get_current_object()

        # Only sysadmins create news and pages, anybody creates an external page
        post.permissions["edit"].test()
        post.save()
        return post, 201


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

        posts: list[Post] = Post.objects(kind="news").visible().order_by("-published").limit(15)
        for post in posts:
            feed.add_item(
                post.name,
                unique_id=post.url_for(_useId=True),
                description=post.headline,
                content=str(md(post.content)),
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
    @api.marshal_with(Post.__read_fields__)
    def get(self, post):
        """Get a given post"""
        if not post.permissions["read"].can():
            api.abort(404)
        return post

    @api.doc("update_post")
    @api.secure
    @api.expect(Post.__write_fields__)
    @api.marshal_with(Post.__read_fields__)
    @api.response(400, "Validation error")
    def put(self, post):
        """Update a given post"""
        post.permissions["edit"].test()
        return patch_and_save(post, request)

    @api.secure
    @api.doc("delete_post")
    @api.response(204, "Object deleted")
    def delete(self, post):
        """Delete a given post"""
        post.permissions["delete"].test()
        post.delete()
        return "", 204


@ns.route("/<post:post>/publish/", endpoint="publish_post")
class PublishPostAPI(API):
    @api.secure
    @api.doc("publish_post")
    @api.marshal_with(Post.__read_fields__)
    def post(self, post):
        """Publish an existing post"""
        post.permissions["edit"].test()
        post.published = datetime.now(UTC)
        post.save()
        return post

    @api.secure
    @api.doc("unpublish_post")
    @api.marshal_with(Post.__read_fields__)
    def delete(self, post):
        """Unpublish an existing post"""
        post.permissions["edit"].test()
        post.published = None
        post.save()
        return post


@ns.route("/<post:post>/image/", endpoint="post_image")
class PostImageAPI(API):
    @api.secure
    @api.doc("post_image")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def post(self, post):
        """Upload a new image"""
        post.permissions["edit"].test()
        parse_uploaded_image(post.image)
        post.save()
        return post

    @api.secure
    @api.doc("resize_post_image")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def put(self, post):
        """Set the image BBox"""
        post.permissions["edit"].test()
        parse_uploaded_image(post.image)
        return post
