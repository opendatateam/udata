from datetime import UTC, datetime

from flask_restx.inputs import boolean
from flask_security import current_user

from udata.api import API, api, fields
from udata.api_fields import patch, patch_and_save, wrap_primary_key
from udata.core.legal.mails import add_send_legal_notice_argument, send_legal_notice_on_deletion
from udata.core.organization.models import Organization
from udata.core.owned import check_organization_is_valid_for_current_user
from udata.utils import id_or_404

from .models import (
    Discussion,
    Message,
)

ns = api.namespace("discussions", "Discussion related operations")


# Input model only used for the POST /discussions/ payload, which doesn't match
# Discussion.__write_fields__: the top-level `comment` ends up inside the first
# Message of the discussion, not on the Discussion itself.
start_discussion_fields = api.model(
    "DiscussionStart",
    {
        "title": fields.String(description="The title of the discussion to open", required=True),
        "comment": fields.String(description="The content of the initial comment", required=True),
        "subject": fields.Nested(
            api.model_reference, description="The discussion target object", required=True
        ),
        "organization": fields.Nested(
            Organization.__ref_fields__,
            allow_null=True,
            description="Publish in the name of this organization",
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
    },
)

comment_discussion_fields = api.model(
    "DiscussionResponse",
    {
        "comment": fields.String(description="The comment to submit", required=True),
        "organization": fields.Nested(
            Organization.__ref_fields__,
            allow_null=True,
            description="Publish in the name of this organization",
        ),
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

discussion_delete_parser = add_send_legal_notice_argument(api.parser())


@ns.route("/<id>/", endpoint="discussion")
class DiscussionAPI(API):
    """
    Base class for a discussion thread.
    """

    @api.doc("get_discussion")
    @api.marshal_with(Discussion.__read_fields__)
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
    @api.marshal_with(Discussion.__read_fields__)
    def post(self, id):
        """Add comment and optionally close a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        if discussion.closed:
            api.abort(403, "Can't add comments on a closed discussion")

        data = api.json_payload()
        close = boolean(data["close"]) if data.get("close") is not None else False
        comment = data.get("comment")

        if not close and not comment:
            api.abort(
                400, "Can only close without message. Please provide either `close` or a `comment`."
            )

        # `posted_by_organization` and `closed_by_organization` are readonly on the models,
        # so the generic `patch()` flow cannot reach them: resolve the organization here.
        organization = wrap_primary_key(
            "organization", Discussion.organization, data.get("organization")
        )
        if organization:
            check_organization_is_valid_for_current_user(organization)

        message_idx = None
        if comment:
            message = Message(
                content=comment,
                posted_by=current_user.id,
                posted_by_organization=organization,
            )
            discussion.discussion.append(message)
            message_idx = len(discussion.discussion) - 1

        if close:
            discussion.permissions["close"].test()
            discussion.closed_by = current_user._get_current_object()
            discussion.closed_by_organization = organization
            discussion.closed = datetime.now(UTC)

        discussion.save()
        if close:
            discussion.signal_close(message=message_idx)
        else:
            discussion.signal_comment(message=message_idx)
        return discussion

    @api.secure
    @api.doc("update_discussion")
    @api.response(403, "Not allowed to update this discussion")
    @api.expect(edit_discussion_fields)
    @api.marshal_with(Discussion.__read_fields__)
    def put(self, id):
        """Update a discussion given its ID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        discussion.permissions["edit"].test()

        return patch_and_save(discussion, {"title": api.json_payload().get("title")})

    @api.secure
    @api.doc("delete_discussion")
    @api.expect(discussion_delete_parser)
    @api.response(403, "Not allowed to delete this discussion")
    def delete(self, id):
        """Delete a discussion given its ID"""
        args = discussion_delete_parser.parse_args()
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        discussion.permissions["delete"].test()
        send_legal_notice_on_deletion(discussion, args)

        discussion.delete()
        return "", 204


message_delete_parser = add_send_legal_notice_argument(api.parser())


@ns.route("/<id>/comments/<cidx>/", endpoint="discussion_comment")
class DiscussionCommentAPI(API):
    """
    Base class for a comment in a discussion thread.
    """

    def _resolve_message(self, discussion, cidx):
        """Resolve a comment identifier (index or UUID) to the message."""
        try:
            idx = int(cidx)
        except ValueError:
            for message in discussion.discussion:
                if str(message.id) == cidx:
                    return message
            api.abort(404, "Comment does not exist")
        else:
            if idx < 0 or idx >= len(discussion.discussion):
                api.abort(404, "Comment does not exist")
            return discussion.discussion[idx]

    @api.secure
    @api.doc("edit_discussion_comment")
    @api.response(403, "Not allowed to edit this comment")
    @api.expect(edit_comment_discussion_fields)
    @api.marshal_with(Discussion.__read_fields__)
    def put(self, id, cidx):
        """Edit a comment given its index or UUID"""
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        message = self._resolve_message(discussion, cidx)
        message.permissions["edit"].test()

        patch(message, {"content": api.json_payload().get("comment")})
        message.last_modified_at = datetime.now(UTC)
        discussion.save()
        return discussion

    @api.secure
    @api.doc("delete_discussion_comment")
    @api.expect(message_delete_parser)
    @api.response(403, "Not allowed to delete this comment")
    def delete(self, id, cidx):
        """Delete a comment given its index or UUID"""
        args = message_delete_parser.parse_args()
        discussion = Discussion.objects.get_or_404(id=id_or_404(id))
        message = self._resolve_message(discussion, cidx)
        if message == discussion.discussion[0]:
            api.abort(400, "You cannot delete the first comment of a discussion")

        message.permissions["delete"].test()
        send_legal_notice_on_deletion(message, args)

        discussion.remove_message(message.id)
        return "", 204


@ns.route("/", endpoint="discussions")
class DiscussionsAPI(API):
    """
    Base class for a list of discussions.
    """

    @api.doc("list_discussions")
    @api.expect(Discussion.__index_parser__)
    @api.marshal_with(Discussion.__page_fields__)
    def get(self):
        """List all Discussions"""
        return Discussion.apply_pagination(Discussion.apply_sort_filters(Discussion.objects))

    @api.secure
    @api.doc("create_discussion")
    @api.expect(start_discussion_fields)
    @api.marshal_with(Discussion.__read_fields__)
    def post(self):
        """Create a new Discussion"""
        data = api.json_payload()

        # `comment` lives in the top-level payload but ends up inside the first Message,
        # which is why we cannot rely on Discussion's `patch()` alone for it. The message
        # goes through `patch()` too, so that an empty comment is rejected here like it is
        # on the other endpoints.
        discussion = patch(Discussion(), data)
        discussion.user = current_user._get_current_object()
        message = Message(
            posted_by=current_user.id,
            posted_by_organization=discussion.organization,
        )
        discussion.discussion = [patch(message, {"content": data.get("comment")})]

        discussion.save()
        discussion.signal_new()

        return discussion, 201
