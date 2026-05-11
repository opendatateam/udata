import fnmatch
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from flask import current_app, url_for
from flask_login import current_user
from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import (
    DateTimeField,
    EmbeddedDocumentField,
    GenericReferenceField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_save

from udata.core.linkable import Linkable
from udata.core.spam.models import SpamMixin, spam_protected
from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.uuid_fields import AutoUUIDField

from .signals import (
    on_discussion_closed,
    on_discussion_deleted,
    on_discussion_message_deleted,
    on_new_discussion,
    on_new_discussion_comment,
)

log = logging.getLogger(__name__)


class Message(SpamMixin, EmbeddedDocument):
    verbose_name = _("message")

    id = AutoUUIDField()
    content = StringField(required=True)
    posted_on = DateTimeField(default=lambda: datetime.now(UTC), required=True)
    posted_by = ReferenceField("User")
    posted_by_organization = ReferenceField("Organization")
    last_modified_at = DateTimeField()

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

        message += f" sur la discussion « [{discussion.title}]({discussion.url_for()}) »"
        return message


def is_valid_notification_external_url(url) -> bool:
    """True if `url` is an http(s) URL whose domain is in the allow-list.

    Used both as the write-time validator (via `NotificationExtra`) and the
    read-time filter (in `Discussion.notification_url`). Keeping a single
    source of truth means a config change is reflected on both sides.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    # Reject non-http(s) schemes: `urlparse("javascript://host/...").netloc`
    # returns the host, so the netloc allow-list alone would let dangerous
    # schemes land in a clickable `<a href>` in the notification mail.
    if parsed.scheme not in ("http", "https"):
        return False
    # Reject any userinfo: `urlparse("http://attacker.com\@eco.example.com")`
    # keeps `attacker.com\` as `username` and `eco.example.com` as `hostname`,
    # but WHATWG-conformant clients (browsers, mail readers) normalize `\` to
    # `/` for http(s), routing the click to `attacker.com`. Userinfo also has
    # no legitimate use in a notification URL, so we reject it outright.
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    allowed = current_app.config.get("DISCUSSION_ALLOWED_EXTERNAL_DOMAINS", [])
    # `fnmatchcase` keeps the match deterministic across OSes (`fnmatch` is
    # case-insensitive on Windows). `hostname` is already lowercased by Python.
    return any(fnmatch.fnmatchcase(host, pattern) for pattern in allowed)


def _validate_notification_external_url(value):
    if not is_valid_notification_external_url(value):
        raise ValidationError("Invalid or disallowed notification.external_url")


def is_valid_notification_model_name(subject, name) -> bool:
    """True if `name` is allow-listed as a `model_name` for `subject`'s class.

    Used both by the form validator (write-time) and `notification_subject_type`
    (read-time). The per-class allow-list prevents a label intended for one
    subject type (e.g. "bouquet" for Topic) from being applied to a different
    one (e.g. a Dataset relabeled as "bouquet").
    """
    if not name:
        return False
    subject_cls = type(subject).__name__ if subject is not None else None
    allowed_per_class = current_app.config.get("DISCUSSION_ALTERNATE_MODEL_NAMES", {})
    return name in allowed_per_class.get(subject_cls, [])


class NotificationExtra(EmbeddedDocument):
    """Typed sub-document of `Discussion.extras["notification"]`.

    `external_url` is validated here (self-contained allow-list check).
    `model_name` carries no validator at this layer because the per-class
    allow-list check needs the discussion's subject, which is not reachable
    from inside an `EmbeddedDocument` validator — it stays in the form.
    """

    external_url = StringField(validation=_validate_notification_external_url)
    model_name = StringField()


class Discussion(SpamMixin, Linkable, Document):
    verbose_name = _("discussion")

    user = ReferenceField("User")
    organization = ReferenceField("Organization")

    subject = GenericReferenceField()
    title = StringField(required=True)
    discussion = ListField(EmbeddedDocumentField(Message))
    created = DateTimeField(default=lambda: datetime.now(UTC), required=True)
    closed = DateTimeField()
    closed_by = ReferenceField("User")
    closed_by_organization = ReferenceField("Organization")
    extras = ExtrasField({"notification": NotificationExtra})

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

    def self_web_url(self, **kwargs):
        return self.subject.self_web_url(append="/discussions", discussion_id=self.id, **kwargs)

    def self_api_url(self, **kwargs):
        return url_for("api.discussion", id=self.id, **self._self_api_url_kwargs(**kwargs))

    def _notification_meta(self) -> dict:
        """Return `extras["notification"]` as a dict, coercing missing/None to {}.

        Raw DB writes (imports, migrations) bypassing mongoengine validation
        can leave the key set to `None`, so both layers are coerced on read.
        """
        return (self.extras or {}).get("notification") or {}

    @property
    def notification_subject_type(self):
        """Subject type label used in notification emails.

        Returns the value of `extras.notification.model_name` when it passes
        the per-class allow-list check, otherwise the subject's `verbose_name`.
        """
        meta_name = self._notification_meta().get("model_name")
        if is_valid_notification_model_name(self.subject, meta_name):
            return meta_name
        return self.subject.verbose_name

    def notification_url(self):
        """URL to point to in notification emails.

        Falls back to `url_for()` when no valid external URL is provided.
        Returns None when the subject has no canonical udata page (e.g. Topic)
        and no valid external URL is provided — in that case the caller should
        skip the notification entirely.

        Defense in depth: re-validate the stored `external_url` at read-time.
        Data written before the validator existed, raw DB writes (imports,
        migrations), or a config change tightening the allow-list could all
        leave an unsafe URL in storage.
        """
        from .constants import NOTIFY_REQUIRES_EXTERNAL_URL

        meta_url = self._notification_meta().get("external_url")
        if is_valid_notification_external_url(meta_url):
            return f"{meta_url}#discussion-{self.id}"
        if isinstance(self.subject, NOTIFY_REQUIRES_EXTERNAL_URL):
            return None
        return self.url_for()

    def spam_report_message(self, breadcrumb):
        message = f"Spam potentiel sur la discussion « [{self.title}]({self.url_for()}) »"
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
