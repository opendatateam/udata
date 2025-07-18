from datetime import datetime
from itertools import chain

from blinker import Signal
from flask import url_for
from mongoengine.signals import post_save, pre_save
from werkzeug.utils import cached_property

from udata.api_fields import field
from udata.core.activity.models import Auditable
from udata.core.badges.models import Badge, BadgeMixin, BadgesList
from udata.core.linkable import Linkable
from udata.core.metrics.helpers import get_stock_metrics
from udata.core.metrics.models import WithMetrics
from udata.core.storages import avatars, default_image_basename
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.mongo import db
from udata.uris import cdata_url

from .constants import (
    ASSOCIATION,
    CERTIFIED,
    COMPANY,
    DEFAULT_ROLE,
    LOCAL_AUTHORITY,
    LOGO_MAX_SIZE,
    LOGO_SIZES,
    MEMBERSHIP_STATUS,
    ORG_BID_SIZE_LIMIT,
    ORG_ROLES,
    PUBLIC_SERVICE,
)

__all__ = ("Organization", "Team", "Member", "MembershipRequest")

BADGES: dict[str, str] = {
    PUBLIC_SERVICE: _("Public Service"),
    CERTIFIED: _("Certified"),
    ASSOCIATION: _("Association"),
    COMPANY: _("Company"),
    LOCAL_AUTHORITY: _("Local authority"),
}


class Team(db.EmbeddedDocument):
    name = db.StringField(required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from="name", update=True, unique=False
    )
    description = db.StringField()

    members = db.ListField(db.ReferenceField("User"))


class Member(db.EmbeddedDocument):
    user = db.ReferenceField("User")
    role = db.StringField(choices=list(ORG_ROLES), default=DEFAULT_ROLE)
    since = db.DateTimeField(default=datetime.utcnow, required=True)

    @property
    def label(self):
        return ORG_ROLES[self.role]


class MembershipRequest(db.EmbeddedDocument):
    """
    Pending organization membership requests
    """

    id = db.AutoUUIDField()
    user = db.ReferenceField("User")
    status = db.StringField(choices=list(MEMBERSHIP_STATUS), default="pending")

    created = db.DateTimeField(default=datetime.utcnow, required=True)

    handled_on = db.DateTimeField()
    handled_by = db.ReferenceField("User")

    comment = db.StringField()
    refusal_comment = db.StringField()

    @property
    def status_label(self):
        return MEMBERSHIP_STATUS[self.status]


class OrganizationQuerySet(db.BaseQuerySet):
    def visible(self):
        return self(deleted=None)

    def hidden(self):
        return self(deleted__ne=None)

    def get_by_id_or_slug(self, id_or_slug):
        return self(slug=id_or_slug).first() or self(id=id_or_slug).first()

    def with_badge(self, kind):
        return self(badges__kind=kind)


def validate_badge(value):
    if value not in Organization.__badges__.keys():
        raise db.ValidationError("Unknown badge type")


class OrganizationBadge(Badge):
    kind = db.StringField(required=True, validation=validate_badge)


class OrganizationBadgeMixin(BadgeMixin):
    badges = field(BadgesList(OrganizationBadge), **BadgeMixin.default_badges_list_params)
    __badges__ = BADGES


class Organization(
    Auditable, WithMetrics, OrganizationBadgeMixin, Linkable, db.Datetimed, db.Document
):
    name = field(db.StringField(required=True))
    acronym = field(db.StringField(max_length=128))
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
    )
    description = field(db.StringField(required=True))
    url = field(db.URLField())
    image_url = field(db.StringField())
    logo = field(
        db.ImageField(
            fs=avatars,
            basename=default_image_basename,
            max_size=LOGO_MAX_SIZE,
            thumbnails=LOGO_SIZES,
        )
    )
    business_number_id = field(db.StringField(max_length=ORG_BID_SIZE_LIMIT))

    members = field(db.ListField(db.EmbeddedDocumentField(Member)))
    teams = field(db.ListField(db.EmbeddedDocumentField(Team)))
    requests = field(db.ListField(db.EmbeddedDocumentField(MembershipRequest)))

    ext = field(db.MapField(db.GenericEmbeddedDocumentField()))
    zone = field(db.StringField())
    extras = field(db.OrganizationExtrasField(), auditable=False)

    deleted = field(db.DateTimeField())

    meta = {
        "indexes": [
            "$name",
            "created_at",
            "slug",
            "metrics.reuses",
            "metrics.datasets",
            "metrics.followers",
            "metrics.views",
            "last_modified",
        ],
        "ordering": ["-created_at"],
        "queryset_class": OrganizationQuerySet,
        "auto_create_index_on_save": True,
    }

    def __str__(self):
        return self.name or ""

    __metrics_keys__ = [
        "dataservices",
        "dataservices_by_months",
        "datasets",
        "datasets_by_months",
        "datasets_followers_by_months",
        "datasets_reuses_by_months",
        "members",
        "reuses",
        "reuses_by_months",
        "reuses_followers_by_months",
        "dataservices",
        "followers",
        "views",
    ]

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    def self_web_url(self, **kwargs):
        return cdata_url(f"/organizations/{self._link_id(**kwargs)}/", **kwargs)

    def self_api_url(self, **kwargs):
        return url_for(
            "api.organization", org=self._link_id(**kwargs), **self._self_api_url_kwargs(**kwargs)
        )

    @property
    def pending_requests(self):
        return [r for r in self.requests if r.status == "pending"]

    @property
    def refused_requests(self):
        return [r for r in self.requests if r.status == "refused"]

    @property
    def accepted_requests(self):
        return [r for r in self.requests if r.status == "accepted"]

    @property
    def certified(self):
        return any(b.kind == CERTIFIED for b in self.badges)

    @property
    def public_service(self):
        is_public_service = any(b.kind == PUBLIC_SERVICE for b in self.badges)
        return self.certified and is_public_service

    @property
    def company(self):
        return any(b.kind == COMPANY for b in self.badges)

    @property
    def association(self):
        return any(b.kind == ASSOCIATION for b in self.badges)

    @property
    def local_authority(self):
        return any(b.kind == LOCAL_AUTHORITY for b in self.badges)

    def member(self, user):
        for member in self.members:
            if member.user == user:
                return member
        return None

    def is_member(self, user):
        return self.member(user) is not None

    def is_admin(self, user):
        member = self.member(user)
        return member is not None and member.role == "admin"

    def pending_request(self, user):
        for request in self.requests:
            if request.user == user and request.status == "pending":
                return request
        return None

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    def by_role(self, role):
        return filter(lambda m: m.role == role, self.members)

    def check_availability(self):
        from udata.models import Dataset  # Circular imports.

        # Performances: only check the first 20 datasets for now.
        return chain(
            *[
                dataset.check_availability()
                for dataset in Dataset.objects(organization=self).visible()[:20]
            ]
        )

    @cached_property
    def json_ld(self):
        type_ = "GovernmentOrganization" if self.public_service else "Organization"

        result = {
            "@context": "http://schema.org",
            "@type": type_,
            "@id": str(self.id),
            "alternateName": self.slug,
            "url": self.url_for(),
            "name": self.name,
            "dateCreated": self.created_at.isoformat(),
            "dateModified": self.last_modified.isoformat(),
        }

        if self.description:
            result["description"] = mdstrip(self.description)

        logo = self.logo(external=True)
        if logo:
            result["logo"] = logo

        return result

    @property
    def views_count(self):
        return self.metrics.get("views", 0)

    def count_members(self):
        self.metrics["members"] = len(self.members)
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_datasets(self):
        from udata.models import Dataset, Follow, Reuse

        self.metrics["datasets"] = Dataset.objects(organization=self).visible().count()
        self.metrics["datasets_by_months"] = get_stock_metrics(
            Dataset.objects(organization=self).visible(), date_label="created_at_internal"
        )
        self.metrics["datasets_followers_by_months"] = get_stock_metrics(
            Follow.objects(following__in=Dataset.objects(organization=self)), date_label="since"
        )
        self.metrics["datasets_reuses_by_months"] = get_stock_metrics(
            Reuse.objects(datasets__in=Dataset.objects(organization=self)).visible()
        )

        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_reuses(self):
        from udata.models import Follow, Reuse

        self.metrics["reuses"] = Reuse.objects(organization=self).visible().count()
        self.metrics["reuses_by_months"] = get_stock_metrics(
            Reuse.objects(organization=self).visible()
        )
        self.metrics["reuses_followers_by_months"] = get_stock_metrics(
            Follow.objects(following__in=Reuse.objects(organization=self)), date_label="since"
        )
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_dataservices(self):
        from udata.models import Dataservice

        self.metrics["dataservices"] = Dataservice.objects(organization=self).visible().count()
        self.metrics["dataservices_by_months"] = get_stock_metrics(
            Dataservice.objects(organization=self).visible(), date_label="created_at"
        )
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_followers(self):
        from udata.models import Follow

        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.save(signal_kwargs={"ignores": ["post_save"]})


pre_save.connect(Organization.pre_save, sender=Organization)
post_save.connect(Organization.post_save, sender=Organization)
