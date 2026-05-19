import logging
from datetime import UTC, datetime

from flask import url_for
from flask_login import current_user
from mongoengine import EmbeddedDocument
from mongoengine.fields import (
    DateTimeField,
    EmbeddedDocumentField,
    GenericReferenceField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_save

from udata.api import api, fields
from udata.api_fields import field, generate_fields
from udata.core.linkable import Linkable
from udata.core.organization.models import Organization
from udata.core.owned import check_organization_is_valid_for_current_user
from udata.core.spam.models import SpamMixin, spam_protected
from udata.core.user.api_fields import user_ref_fields
from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.uuid_fields import AutoUUIDField

from .constants import COMMENT_SIZE_LIMIT
from .signals import (
    on_discussion_closed,
    on_discussion_deleted,
    on_discussion_message_deleted,
    on_new_discussion,
    on_new_discussion_comment,
)

log = logging.getLogger(__name__)


message_permissions_fields = api.model(
    "DiscussionMessagePermissions",
    {"delete": fields.Permission(), "edit": fields.Permission()},
)

discussion_permissions_fields = api.model(
    "DiscussionPermissions",
    {"delete": fields.Permission(), "edit": fields.Permission(), "close": fields.Permission()},
)


@generate_fields()
class Message(SpamMixin, EmbeddedDocument):
    verbose_name = _("message")

    id = field(AutoUUIDField(), readonly=True)
    content = field(StringField(required=True, max_length=COMMENT_SIZE_LIMIT))
    posted_on = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
    )
    posted_by = field(
        ReferenceField("User"),
        readonly=True,
        nested_fields=user_ref_fields,
        allow_null=True,
    )
    posted_by_organization = field(
        ReferenceField("Organization"),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        allow_null=True,
    )
    last_modified_at = field(DateTimeField(), readonly=True, allow_null=True)

    @property
    @field(nested_fields=message_permissions_fields)
    def permissions(self):
        from .permissions import DiscussionMessagePermission

        return {
            "delete": DiscussionMessagePermission(self),
            "edit": DiscussionMessagePermission(self),
        }

    @property
    def posted_by_name(self):
        return (
            self.posted_by_organization.name
            if self.posted_by_organization
            else self.posted_by.fullname
        )

    @property
    def posted_by_org_or_user(self):
        return self.posted_by_organization or self.posted_by

    def fields_to_check_for_spam(self):
        return {"content": self.content}

    def spam_report_message(self, breadcrumb):
        message = "Spam potentiel dans le message"
        if self.posted_by_org_or_user:
            message += f" de [{self.posted_by_name}]({self.posted_by_org_or_user.url_for()})"

        if len(breadcrumb) != 2:
            log.warning(
                f"`spam_report_message` called on message with a breadcrumb of {len(breadcrumb)} elements.",
                extra={"breadcrumb": breadcrumb},
            )
            return message

        discussion = breadcrumb[0]
        if not isinstance(discussion, Discussion):
            log.warning(
                "`spam_report_message` called on message with a breadcrumb not containing a Discussion at index 0.",
                extra={"breadcrumb": breadcrumb},
            )
            return message

        message += f" sur la discussion « [{discussion.title}]({discussion.url_for()}) »"
        return message


@generate_fields()
class Discussion(SpamMixin, Linkable, Document):
    verbose_name = _("discussion")

    user = field(
        ReferenceField("User"),
        readonly=True,
        nested_fields=user_ref_fields,
        allow_null=True,
        description="The discussion author",
    )
    organization = field(
        ReferenceField("Organization"),
        nested_fields=Organization.__ref_fields__,
        allow_null=True,
        description="The organization to publish on behalf of",
        checks=[check_organization_is_valid_for_current_user],
    )

    subject = field(
        GenericReferenceField(required=True),
        nested_fields=api.model_reference,
        description="The discussion target object",
    )
    title = field(StringField(required=True), description="The discussion title")
    discussion = field(
        ListField(EmbeddedDocumentField(Message)),
        readonly=True,
        description="The list of messages in the discussion",
    )
    created = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        description="The discussion creation date",
    )
    closed = field(
        DateTimeField(),
        readonly=True,
        allow_null=True,
        description="The discussion closing date",
    )
    closed_by = field(
        ReferenceField("User"),
        readonly=True,
        nested_fields=user_ref_fields,
        allow_null=True,
        description="The user who closed the discussion",
    )
    closed_by_organization = field(
        ReferenceField("Organization"),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        allow_null=True,
        description="The organization who closed the discussion",
    )
    extras = field(ExtrasField(), description="Extra attributes as key-value pairs")

    meta = {
        "indexes": [
            {
                "fields": ["$title", "$discussion.content"],
                "default_language": "french",
                "weights": {"title": 10, "discussion.content": 5},
            },
            "user",
            "subject",
            "-created",
        ],
        "ordering": ["-created"],
        "auto_create_index_on_save": True,
    }

    @property
    @field(nested_fields=discussion_permissions_fields)
    def permissions(self):
        from udata.core.discussions.permissions import (
            DiscussionAuthorOrSubjectOwnerPermission,
            DiscussionAuthorPermission,
        )

        return {
            "delete": DiscussionAuthorPermission(self),
            # To edit the title of a discussion we need to be the owner of the first message
            "edit": DiscussionAuthorPermission(self),
            "close": DiscussionAuthorOrSubjectOwnerPermission(self),
        }

    @field(description="The discussion API URI")
    def url(self):
        return self.self_api_url()

    @property
    def closed_by_name(self):
        if self.closed_by_organization:
            return self.closed_by_organization.name

        if self.closed_by:
            return self.closed_by.fullname

        return None

    @property
    def closed_by_org_or_user(self):
        return self.closed_by_organization or self.closed_by

    def person_involved(self, person):
        """Return True if the given person has been involved in the

        discussion, False otherwise.
        """
        return any(message.posted_by == person for message in self.discussion)

    def fields_to_check_for_spam(self):
        fields = {"title": self.title}
        # Discussion should always have a first message but it's not the case in some tests…
        if len(self.discussion):
            fields["discussion.0.content"] = self.discussion[0].content
        return fields

    def embeds_to_check_for_spam(self):
        return self.discussion[1:]

    def spam_is_whitelisted(self) -> bool:
        from udata.core.dataset.permissions import OwnablePermission
        from udata.core.owned import Owned

        if not current_user or not current_user.is_authenticated:
            return False

        if not isinstance(self.subject, Owned):
            return False

        # When creating a new Discussion the `subject` is an empty model
        # with only `id`. We need to fetch it from the database to have
        # all the required information
        if not self.subject.owner or not self.subject.organization:
            self.subject.reload()

        return OwnablePermission(self.subject).can()

    @field(description="The discussion web URL")
    def self_web_url(self, **kwargs):
        return self.subject.self_web_url(append="/discussions", discussion_id=self.id, **kwargs)

    def self_api_url(self, **kwargs):
        return url_for("api.discussion", id=self.id, **self._self_api_url_kwargs(**kwargs))

    def spam_report_message(self, breadcrumb):
        message = f"Spam potentiel sur la discussion « [{self.title}]({self.url_for()}) »"
        if self.user:
            message += f" de [{self.user.fullname}]({self.user.url_for()})"

        return message

    def owner_recipients(self, sender=None):
        """Return the list of users that should be notified about this discussion."""
        recipients = {m.posted_by.id: m.posted_by for m in self.discussion}
        if getattr(self.subject, "organization", None):
            for member in self.subject.organization.members:
                recipients[member.user.id] = member.user
        elif getattr(self.subject, "owner", None):
            recipients[self.subject.owner.id] = self.subject.owner

        if sender:
            recipients.pop(sender.id, None)
        return list(recipients.values())

    @spam_protected()
    def signal_new(self):
        on_new_discussion.send(self)

    @spam_protected(lambda discussion, message: discussion.discussion[message] if message else None)
    def signal_close(self, message):
        on_discussion_closed.send(self, message=message)

    @spam_protected(lambda discussion, message: discussion.discussion[message])
    def signal_comment(self, message):
        on_new_discussion_comment.send(self, message=message)

    def delete(self, *args, **kwargs):
        """Delete the discussion and send deletion signal"""
        result = super().delete(*args, **kwargs)
        on_discussion_deleted.send(self)
        return result

    def remove_message(self, message_id):
        """Remove a message by its UUID and trigger deletion signal"""
        for i, message in enumerate(self.discussion):
            if message.id == message_id:
                self.discussion.pop(i)
                self.save()

                from udata.core.reports.models import Report

                Report.mark_subject_deleted_by_embed_id(self, message.id)

                on_discussion_message_deleted.send(self, message=message)
                return


post_save.connect(Discussion.post_save, sender=Discussion)
