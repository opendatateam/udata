import json
from copy import copy
from datetime import datetime
from itertools import chain
from time import time

from authlib.jose import JsonWebSignature
from blinker import Signal
from flask import current_app
from flask_security import MongoEngineUserDatastore, RoleMixin, UserMixin
from mongoengine.signals import post_save, pre_save
from werkzeug.utils import cached_property

from udata import mail
from udata.api_fields import field
from udata.core import storages
from udata.core.discussions.models import Discussion
from udata.core.storages import avatars, default_image_basename
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.mail import get_mail_campaign_dict
from udata.models import Follow, WithMetrics, db
from udata.uris import endpoint_for

from .constants import AVATAR_SIZES

__all__ = ("User", "Role", "datastore")


# TODO: use simple text for role
class Role(db.Document, RoleMixin):
    ADMIN = "admin"
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)
    permissions = db.ListField()

    def __str__(self):
        return self.name


class UserSettings(db.EmbeddedDocument):
    prefered_language = db.StringField()


class User(WithMetrics, UserMixin, db.Document):
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="fullname"), auditable=False
    )
    email = field(db.StringField(max_length=255, required=True, unique=True))
    password = field(db.StringField())
    active = field(db.BooleanField())
    fs_uniquifier = field(db.StringField(max_length=64, unique=True, sparse=True))
    roles = field(db.ListField(db.ReferenceField(Role), default=[]))

    first_name = field(db.StringField(max_length=255, required=True))
    last_name = field(db.StringField(max_length=255, required=True))

    avatar_url = field(db.URLField())
    avatar = field(
        db.ImageField(fs=avatars, basename=default_image_basename, thumbnails=AVATAR_SIZES)
    )
    website = field(db.URLField())
    about = field(db.StringField())

    prefered_language = field(db.StringField())

    apikey = field(db.StringField())

    created_at = field(db.DateTimeField(default=datetime.utcnow, required=True), auditable=False)

    # The field below is required for Flask-security
    # when SECURITY_CONFIRMABLE is True
    confirmed_at = field(db.DateTimeField(), auditable=False)

    password_rotation_demanded = field(db.DateTimeField(), auditable=False)
    password_rotation_performed = field(db.DateTimeField(), auditable=False)

    # The 5 fields below are required for Flask-security
    # when SECURITY_TRACKABLE is True
    last_login_at = field(db.DateTimeField(), auditable=False)
    current_login_at = field(db.DateTimeField(), auditable=False)
    last_login_ip = field(db.StringField(), auditable=False)
    current_login_ip = field(db.StringField(), auditable=False)
    login_count = field(db.IntField(), auditable=False)

    deleted = field(db.DateTimeField())
    ext = field(db.MapField(db.GenericEmbeddedDocumentField()))
    extras = field(db.ExtrasField(), auditable=False)

    # Used to track notification for automatic inactive users deletion
    # when YEARS_OF_INACTIVITY_BEFORE_DELETION is set
    inactive_deletion_notified_at = field(db.DateTimeField(), auditable=False)

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    meta = {
        "indexes": ["$slug", "-created_at", "slug", "apikey"],
        "ordering": ["-created_at"],
        "auto_create_index_on_save": True,
    }

    __metrics_keys__ = [
        "datasets",
        "reuses",
        "dataservices",
        "following",
        "followers",
    ]

    def __str__(self):
        return self.fullname

    @property
    def fullname(self):
        return " ".join((self.first_name or "", self.last_name or "")).strip()

    @cached_property
    def organizations(self):
        from udata.core.organization.models import Organization

        return Organization.objects(members__user=self, deleted__exists=False)

    @property
    def sysadmin(self):
        return self.has_role("admin")

    def url_for(self, *args, **kwargs):
        return endpoint_for("users.show", "api.user", user=self, *args, **kwargs)

    display_url = property(url_for)

    @property
    def external_url(self):
        return self.url_for(_external=True)

    @property
    def external_url_with_campaign(self):
        extras = get_mail_campaign_dict()
        return self.url_for(_external=True, **extras)

    @property
    def visible(self):
        count = self.metrics.get("datasets", 0) + self.metrics.get("reuses", 0)
        return count > 0 and self.active

    @cached_property
    def resources_availability(self):
        """Return the percentage of availability for resources."""
        # Flatten the list.
        availabilities = list(chain(*[org.check_availability() for org in self.organizations]))
        # Filter out the unknown
        availabilities = [a for a in availabilities if type(a) is bool]
        if availabilities:
            # Trick will work because it's a sum() of booleans.
            return round(100.0 * sum(availabilities) / len(availabilities), 2)
        # if nothing is unavailable, everything is considered OK
        return 100

    @cached_property
    def datasets_org_count(self):
        """Return the number of datasets of user's organizations."""
        from udata.models import Dataset  # Circular imports.

        return sum(
            Dataset.objects(organization=org).visible().count() for org in self.organizations
        )

    @cached_property
    def followers_org_count(self):
        """Return the number of followers of user's organizations."""
        from udata.models import Follow  # Circular imports.

        return sum(Follow.objects(following=org).count() for org in self.organizations)

    @property
    def datasets_count(self):
        """Return the number of datasets of the user."""
        return self.metrics.get("datasets", 0)

    @property
    def followers_count(self):
        """Return the number of followers of the user."""
        return self.metrics.get("followers", 0)

    def generate_api_key(self):
        payload = {
            "user": str(self.id),
            "time": time(),
        }
        s = JsonWebSignature(algorithms=["HS512"]).serialize_compact(
            {"alg": "HS512"},
            json.dumps(payload, separators=(",", ":")),
            current_app.config["SECRET_KEY"],
        )
        self.apikey = s.decode()

    def clear_api_key(self):
        self.apikey = None

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        if "post_save" in kwargs.get("ignores", []):
            return
        cls.after_save.send(document)
        if kwargs.get("created"):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)

    @cached_property
    def json_ld(self):
        result = {
            "@type": "Person",
            "@context": "http://schema.org",
            "name": self.fullname,
        }

        if self.about:
            result["description"] = mdstrip(self.about)

        if self.avatar_url:
            result["image"] = self.avatar_url

        if self.website:
            result["url"] = self.website

        return result

    def _delete(self, *args, **kwargs):
        return db.Document.delete(self, *args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("""This method should not be using directly.
        Use `mark_as_deleted` (or `_delete` if you know what you're doing)""")

    def mark_as_deleted(self, notify: bool = True, delete_comments: bool = False):
        if self.avatar.filename is not None:
            storage = storages.avatars
            storage.delete(self.avatar.filename)
            storage.delete(self.avatar.original)
            for key, value in self.avatar.thumbnails.items():
                storage.delete(value)

        copied_user = copy(self)
        self.email = "{}@deleted".format(self.id)
        self.slug = "deleted"
        self.password = None
        self.active = False
        self.first_name = "DELETED"
        self.last_name = "DELETED"
        self.avatar = None
        self.avatar_url = None
        self.website = None
        self.about = None
        self.extras = None
        self.apikey = None
        self.deleted = datetime.utcnow()
        self.save()
        for organization in self.organizations:
            organization.members = [
                member for member in organization.members if member.user != self
            ]
            organization.save()
        if delete_comments:
            for discussion in Discussion.objects(discussion__posted_by=self):
                # Remove all discussions with current user as only participant
                if all(message.posted_by == self for message in discussion.discussion):
                    discussion.delete()
                    continue

                for message in discussion.discussion:
                    if message.posted_by == self:
                        message.content = "DELETED"
                discussion.save()
        Follow.objects(follower=self).delete()
        Follow.objects(following=self).delete()

        from udata.models import ContactPoint

        ContactPoint.objects(owner=self).delete()

        if notify:
            mail.send(_("Account deletion"), copied_user, "account_deleted")

    def count_datasets(self):
        from udata.models import Dataset

        self.metrics["datasets"] = Dataset.objects(owner=self).visible().count()
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_reuses(self):
        from udata.models import Reuse

        self.metrics["reuses"] = Reuse.objects(owner=self).visible().count()
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_dataservices(self):
        from udata.core.dataservices.models import Dataservice

        self.metrics["dataservices"] = Dataservice.objects(owner=self).visible().count()
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_followers(self):
        from udata.models import Follow

        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_following(self):
        from udata.models import Follow

        self.metrics["following"] = Follow.objects.following(self).count()
        self.save(signal_kwargs={"ignores": ["post_save"]})


datastore = MongoEngineUserDatastore(db, User, Role)

pre_save.connect(User.pre_save, sender=User)
post_save.connect(User.post_save, sender=User)
