import logging
from datetime import datetime

from flask import url_for
from flask_login import current_user

from udata.core.linkable import Linkable
from udata.core.spam.models import SpamMixin, spam_protected
from udata.mongo import db

from .signals import on_discussion_closed, on_new_discussion, on_new_discussion_comment

log = logging.getLogger(__name__)


class Message(SpamMixin, db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.utcnow, required=True)
    posted_by = db.ReferenceField("User")
    posted_by_organization = db.ReferenceField("Organization")
    last_modified_at = db.DateTimeField()

    @property
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

    def texts_to_check_for_spam(self):
        return [self.content]

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

        message += f" sur la discussion « [{discussion.title}]({discussion.url_for()}) »"
        return message


class Discussion(SpamMixin, Linkable, db.Document):
    user = db.ReferenceField("User")
    organization = db.ReferenceField("Organization")

    subject = db.GenericReferenceField()
    title = db.StringField(required=True)
    discussion = db.ListField(db.EmbeddedDocumentField(Message))
    created = db.DateTimeField(default=datetime.utcnow, required=True)
    closed = db.DateTimeField()
    closed_by = db.ReferenceField("User")
    closed_by_organization = db.ReferenceField("Organization")
    extras = db.ExtrasField()

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

    def texts_to_check_for_spam(self):
        # Discussion should always have a first message but it's not the case in some tests…
        return [self.title, self.discussion[0].content if len(self.discussion) else ""]

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

    def self_web_url(self, **kwargs):
        return self.subject.self_web_url(append="/discussions", discussion_id=self.id, **kwargs)

    def self_api_url(self, **kwargs):
        return url_for("api.discussion", id=self.id, **self._self_api_url_kwargs(**kwargs))

    def spam_report_message(self, breadcrumb):
        message = f"Spam potentiel sur la discussion « [{self.title}]({self.url_for()}) »"
        if self.user:
            message += f" de [{self.user.fullname}]({self.user.url_for()})"

        return message

    @spam_protected()
    def signal_new(self):
        on_new_discussion.send(self)

    @spam_protected(lambda discussion, message: discussion.discussion[message] if message else None)
    def signal_close(self, message):
        on_discussion_closed.send(self, message=message)

    @spam_protected(lambda discussion, message: discussion.discussion[message])
    def signal_comment(self, message):
        on_new_discussion_comment.send(self, message=message)
