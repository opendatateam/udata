from datetime import datetime

from bson import ObjectId
from flask_restx.inputs import boolean
from flask_security import current_user

from udata.api import API, api, fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.core.spam.api import SpamAPIMixin
from udata.core.spam.fields import spam_fields
from udata.core.user.api_fields import user_ref_fields
from udata.utils import id_or_404

from .forms import (
    DiscussionCommentForm,
    DiscussionCreateForm,
    DiscussionEditCommentForm,
    DiscussionEditForm,
)
from .models import Discussion, Message
from .signals import on_discussion_deleted

ns = api.namespace("discussions", "Discussion related operations")


message_permissions_fields = api.model(
    "DiscussionMessagePermissions",
    {"delete": fields.Permission(), "edit": fields.Permission()},
)

message_fields = api.model(
    "DiscussionMessage",
    {
        "content": fields.String(description="The message body"),
        "posted_by": fields.Nested(user_ref_fields, description="The message author"),
        "posted_by_organization": fields.Nested(
            org_ref_fields, description="The organization to show to users", allow_null=True
        ),
        "posted_on": fields.ISODateTime(description="The message posting date"),
        "last_modified_at": fields.ISODateTime(description="The message last edit date"),
        "spam": fields.Nested(spam_fields),
        "permissions": fields.Nested(message_permissions_fields),
    },
)

discussion_permissions_fields = api.model(
    "DiscussionPermissions",
    {"delete": fields.Permission(), "edit": fields.Permission(), "close": fields.Permission()},
)

discussion_fields = api.model(
    "Discussion",
    {
        "id": fields.String(description="The discussion identifier"),
        "subject": fields.Nested(api.model_reference, description="The discussion target object"),
        "class": fields.ClassName(description="The object class", discriminator=True),
        "title": fields.String(description="The discussion title"),
        "user": fields.Nested(user_ref_fields, description="The discussion author"),
        "organization": fields.Nested(
            org_ref_fields, description="The discussion author", allow_null=True
        ),
        "created": fields.ISODateTime(description="The discussion creation date"),
        "closed": fields.ISODateTime(description="The discussion closing date"),
        "closed_by": fields.Nested(
            user_ref_fields, allow_null=True, description="The user who closed the discussion"
        ),
        "closed_by_organization": fields.Nested(
            org_ref_fields,
            allow_null=True,
            description="The organization who closed the discussion",
        ),
        "discussion": fields.Nested(message_fields),
        "url": fields.String(
            attribute=lambda d: d.self_api_url(), description="The discussion API URI"
        ),
        "self_web_url": fields.String(
            attribute=lambda d: d.self_web_url(), description="The discussion web URL"
        ),
        "extras": fields.Raw(description="Extra attributes as key-value pairs"),
        "spam": fields.Nested(spam_fields),
        "permissions": fields.Nested(discussion_permissions_fields),
    },
)

start_discussion_fields = api.model(
    "DiscussionStart",
    {
        "title": fields.String(description="The title of the discussion to open", required=True),
        "comment": fields.String(description="The content of the initial comment", required=True),
        "subject": fields.Nested(
            api.model_reference, description="The discussion target object", required=True
        ),
        "organization": fields.Nested(
            org_ref_fields, allow_null=True, description="Publish in the name of this organization"
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
    },
)

comment_discussion_fields = api.model(
    "DiscussionResponse",
    {
        "comment": fields.String(description="The comment to submit", required=True),
        "close": fields.Boolean(
            description="Is this a closing response. Only subject owner can close"
        ),
    },
)

edit_comment_discussion_fields = api.model(
    "DiscussionEditComment",
    {
        "comment": fields.String(description="The new comment", required=True),
    },
)

edit_discussion_fields = api.model(
    "DiscussionEdit",
    {
        "title": fields.String(description="The new title", required=True),
    },
)

discussion_page_fields = api.model("DiscussionPage", fields.pager(discussion_fields))

parser = api.parser()
sorting_keys: list[str] = ["created", "title", "closed", "discussion.posted_on"]
sorting_choices: list[str] = sorting_keys + ["-" + k for k in sorting_keys]
parser.add_argument("q", type=str, location="args", help="The search query")
parser.add_argument(
    "sort",
    type=str,
    default="-created",
    choices=sorting_choices,
    location="args",
    help="The field (and direction) on which sorting apply",
)
parser.add_argument(
    "closed",
    type=boolean,
    location="args",
    help="Filters discussions on their closed status if specified",
)
parser.add_argument(
    "for", type=str, location="args", action="append", help="Filter discussions for a given subject"
)
parser.add_argument(
    "org", type=str, location="args", help="Filter discussions for a given organization"
)
parser.add_argument("user", type=str, location="args", help="Filter discussions created by a user")
parser.add_argument("page", type=int, default=1, location="args", help="The page to fetch")
parser.add_argument(
    "page_size", type=int, default=20, location="args", help="The page size to fetch"
)


@ns.route("/<id>/spam/", endpoint="discussion_spam")
@ns.doc(delete={"id": "unspam"})
class DiscussionSpamAPI(SpamAPIMixin):
    model = Discussion


@ns.route("/<id>/", endpoint="discussion")
class DiscussionAPI(API):
    """
    Base class for a discussion thread.
    """

    @api.doc("get_discussion")
    @api.marshal_with(discussion_fields)
    def get(self, id):
        """Get a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        return discussion

    @api.secure
    @api.doc("comment_discussion")
    @api.expect(comment_discussion_fields)
    @api.response(
        403, "Not allowed to close this discussion OR can't add comments on a closed discussion"
    )
    @api.marshal_with(discussion_fields)
    def post(self, id):
        """Add comment and optionally close a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        if discussion.closed:
            api.abort(403, "Can't add comments on a closed discussion")
        form = api.validate(DiscussionCommentForm)

        close = form.close.data
        if not close and not form.comment.data:
            api.abort(
                400, "Can only close without message. Please provide either `close` or a `comment`."
            )

        if form.comment.data:
            message = Message(
                content=form.comment.data,
                posted_by=current_user.id,
                posted_by_organization=form.organization.data,
            )
            discussion.discussion.append(message)
            message_idx = len(discussion.discussion) - 1
        else:
            message_idx = None

        if close:
            discussion.permissions["close"].test()
            discussion.closed_by = current_user._get_current_object()
            discussion.closed_by_organization = form.organization.data
            discussion.closed = datetime.utcnow()

        discussion.save()
        if close:
            discussion.signal_close(message=message_idx)
        else:
            discussion.signal_comment(message=message_idx)
        return discussion

    @api.doc("update_discussion")
    @api.response(403, "Not allowed to update this discussion")
    @api.expect(edit_comment_discussion_fields)
    @api.marshal_with(discussion_fields)
    def put(self, id):
        """Update a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        discussion.permissions["edit"].test()

        form = api.validate(DiscussionEditForm, discussion)
        form.save()

        return discussion

    @api.doc("delete_discussion")
    @api.response(403, "Not allowed to delete this discussion")
    def delete(self, id):
        """Delete a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        discussion.permissions["delete"].test()

        discussion.delete()
        on_discussion_deleted.send(discussion)
        return "", 204


@ns.route("/<id>/comments/<int:cidx>/spam", endpoint="discussion_comment_spam")
@ns.doc(delete={"id": "unspam"})
class DiscussionCommentSpamAPI(SpamAPIMixin):
    def get_model(self, id, cidx):
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        if len(discussion.discussion) <= cidx:
            api.abort(404, "Comment does not exist")
        elif cidx == 0:
            api.abort(400, "You cannot unspam the first comment of a discussion")
        return discussion, discussion.discussion[cidx]


@ns.route("/<id>/comments/<int:cidx>", endpoint="discussion_comment")
class DiscussionCommentAPI(API):
    """
    Base class for a comment in a discussion thread.
    """

    @api.doc("edit_discussion_comment")
    @api.response(403, "Not allowed to edit this comment")
    @api.expect(edit_comment_discussion_fields)
    @api.marshal_with(discussion_fields)
    def put(self, id, cidx):
        """Edit a comment given its index"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        if len(discussion.discussion) <= cidx:
            api.abort(404, "Comment does not exist")

        message = discussion.discussion[cidx]
        message.permissions["edit"].test()

        form = api.validate(DiscussionEditCommentForm)

        discussion.discussion[cidx].content = form.comment.data
        discussion.discussion[cidx].last_modified_at = datetime.utcnow()
        discussion.save()
        return discussion

    @api.doc("delete_discussion_comment")
    @api.response(403, "Not allowed to delete this comment")
    def delete(self, id, cidx):
        """Delete a comment given its index"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        if len(discussion.discussion) <= cidx:
            api.abort(404, "Comment does not exist")
        elif cidx == 0:
            api.abort(400, "You cannot delete the first comment of a discussion")

        discussion.discussion[cidx].permissions["delete"].test()

        discussion.discussion.pop(cidx)
        discussion.save()
        return "", 204


@ns.route("/", endpoint="discussions")
class DiscussionsAPI(API):
    """
    Base class for a list of discussions.
    """

    @api.doc("list_discussions")
    @api.expect(parser)
    @api.marshal_with(discussion_page_fields)
    def get(self):
        """List all Discussions"""
        args = parser.parse_args()
        discussions = Discussion.objects
        if args["for"]:
            discussions = discussions.generic_in(subject=args["for"])
        if args["org"]:
            org = Organization.objects.get_or_404(id=id_or_404(args["org"]))
            if not org:
                api.abort(404, "Organization does not exist")
            reuses = Reuse.objects(organization=org).only("id")
            datasets = Dataset.objects(organization=org).only("id")
            dataservices = Dataservice.objects(organization=org).only("id")
            subjects = list(reuses) + list(datasets) + list(dataservices)
            discussions = discussions(subject__in=subjects)
        if args["user"]:
            discussions = discussions(discussion__posted_by=ObjectId(args["user"]))
        if args["closed"] is False:
            discussions = discussions(closed=None)
        elif args["closed"] is True:
            discussions = discussions(closed__ne=None)

        if args["q"]:
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            discussions = discussions.search_text(phrase_query).order_by("$text_score")

        discussions = discussions.order_by(args["sort"])
        return discussions.paginate(args["page"], args["page_size"])

    @api.secure
    @api.doc("create_discussion")
    @api.expect(start_discussion_fields)
    @api.marshal_with(discussion_fields)
    def post(self):
        """Create a new Discussion"""
        form = api.validate(DiscussionCreateForm)

        message = Message(
            content=form.comment.data,
            posted_by=current_user.id,
            posted_by_organization=form.organization.data,
        )
        discussion = Discussion(user=current_user.id, discussion=[message])
        form.populate_obj(discussion)
        discussion.save()

        discussion.signal_new()

        return discussion, 201
