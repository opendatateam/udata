from datetime import UTC, datetime
from itertools import chain

from blinker import Signal
from flask import current_app, url_for
from flask_babel import LazyString
from flask_storage.mongo import ImageField
from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import (
    DateTimeField,
    EmbeddedDocumentField,
    GenericEmbeddedDocumentField,
    GenericReferenceField,
    ListField,
    MapField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_save, pre_save
from werkzeug.utils import cached_property

from udata.api import api
from udata.api import fields as api_fields
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.badges.models import Badge, BadgeMixin, BadgesList
from udata.core.linkable import Linkable
from udata.core.metrics.helpers import get_stock_metrics
from udata.core.metrics.models import WithMetrics
from udata.core.storages import avatars, default_image_basename
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.errors import FieldValidationError
from udata.mongo.extras_fields import OrganizationExtrasField
from udata.mongo.queryset import UDataQuerySet
from udata.mongo.slug_fields import SlugField
from udata.mongo.url_field import URLField
from udata.mongo.uuid_fields import AutoUUIDField
from udata.uris import cdata_url

from .constants import (
    ASSIGNABLE_OBJECT_TYPES,
    ASSOCIATION,
    BIGGEST_LOGO_SIZE,
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
    REQUEST_TYPES,
)

__all__ = ("Organization", "Team", "Member", "MembershipRequest")


def check_siret(value, field, **_kwargs):
    if not value:
        return
    if current_app.config.get("ORG_BID_FORMAT") != "siret":
        return
    siret_number = str(value)
    if len(siret_number) != 14:
        raise FieldValidationError(_("A siret number is made of 14 digits"), field=field)
    # Exception for the french postal service.
    if siret_number == "35600000000048":
        return
    try:
        chiffres = [int(chiffre) for chiffre in siret_number[:9]]
        chiffres[1::2] = [chiffre * 2 for chiffre in chiffres[1::2]]
        chiffres = [chiffre - 9 if chiffre > 9 else chiffre for chiffre in chiffres]
        total = sum(chiffres)
    except ValueError:
        raise FieldValidationError(_("A siret number is only made of digits"), field=field)
    if total % 10 != 0:
        raise FieldValidationError(_("Invalid Siret number"), field=field)


BADGES: dict[str, LazyString] = {
    PUBLIC_SERVICE: _("Public Service"),
    CERTIFIED: _("Certified"),
    ASSOCIATION: _("Association"),
    COMPANY: _("Company"),
    LOCAL_AUTHORITY: _("Local authority"),
}


@generate_fields()
class Team(EmbeddedDocument):
    name = StringField(required=True)
    slug = SlugField(max_length=255, required=True, populate_from="name", update=True, unique=False)
    description = StringField()

    members = ListField(ReferenceField("User"))


@generate_fields()
class Member(EmbeddedDocument):
    user = field(ReferenceField("User"), readonly=True)
    role = field(StringField(choices=list(ORG_ROLES), default=DEFAULT_ROLE))
    since = field(DateTimeField(default=lambda: datetime.now(UTC), required=True), readonly=True)

    @property
    @field(readonly=True)
    def label(self):
        return ORG_ROLES[self.role]


@generate_fields()
class MembershipRequest(EmbeddedDocument):
    """
    Pending organization membership requests or invitations.

    For requests (user asks to join):
        - kind = "request"
        - user = the requesting user
        - created_by = None

    For invitations (org invites user):
        - kind = "invitation"
        - user = the invited user (or None if email invitation)
        - email = email for non-registered users
        - created_by = admin who created the invitation
    """

    id = field(AutoUUIDField(), readonly=True)
    user = field(ReferenceField("User"), allow_null=True, readonly=True)
    status = field(StringField(choices=list(MEMBERSHIP_STATUS), default="pending"), readonly=True)

    created = field(DateTimeField(default=lambda: datetime.now(UTC), required=True), readonly=True)

    handled_on = field(DateTimeField(), readonly=True)
    handled_by = field(ReferenceField("User"), readonly=True)

    comment = field(StringField())
    refusal_comment = field(StringField(), readonly=True)

    kind = field(
        StringField(choices=list(REQUEST_TYPES), default="request"),
        readonly=True,
    )
    email = field(StringField(), readonly=True)
    created_by = field(ReferenceField("User"), readonly=True)
    role = field(StringField(choices=list(ORG_ROLES), default=DEFAULT_ROLE), readonly=True)
    # Not wrapped with field() because GenericReferenceField choices (Dataset, Dataservice, Reuse)
    # are not yet registered at import time. Serialized via manual request_fields in api_fields.py.
    assignments = ListField(GenericReferenceField(choices=ASSIGNABLE_OBJECT_TYPES))

    after_create = Signal()
    after_handle = Signal()

    @property
    def status_label(self):
        return MEMBERSHIP_STATUS[self.status]


class OrganizationQuerySet(UDataQuerySet):
    def visible(self):
        return self(deleted=None)

    def hidden(self):
        return self(deleted__ne=None)

    def get_by_id_or_slug(self, id_or_slug):
        return self(slug=id_or_slug).first() or self(id=id_or_slug).first()

    def with_badge(self, kind):
        return self(badges__kind=kind)


# Uses __badges__ (not available_badges) so that existing badges in DB
# remain valid even if they are hidden via settings.
# Uses a standalone function (not a model method) because OrganizationBadge is
# defined before Organization in the file — Organization is resolved lazily at call time.
def validate_badge(value):
    if value not in Organization.__badges__.keys():
        raise ValidationError("Unknown badge type")


class OrganizationBadge(Badge):
    kind = StringField(required=True, validation=validate_badge)


class OrganizationBadgeMixin(BadgeMixin):
    badges = field(
        BadgesList(OrganizationBadge), show_as_ref=True, **BadgeMixin.default_badges_list_params
    )
    __badges__ = BADGES


org_permissions_fields = api.model(
    "OrganizationPermissions",
    {
        "edit": api_fields.Permission(),
        "delete": api_fields.Permission(),
        "members": api_fields.Permission(),
        "harvest": api_fields.Permission(),
        "private": api_fields.Permission(),
    },
)


@generate_fields()
class Organization(
    Auditable,
    WithMetrics,
    OrganizationBadgeMixin,
    Linkable,
    Datetimed,
    Document[OrganizationQuerySet],
):
    name = field(StringField(required=True), show_as_ref=True)
    acronym = field(StringField(max_length=128), show_as_ref=True)
    slug = field(
        SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
        show_as_ref=True,
        readonly=True,
    )
    description = field(
        StringField(required=True),
        markdown=True,
    )
    url = field(URLField())
    image_url = field(StringField())
    logo = field(
        ImageField(
            fs=avatars,
            basename=default_image_basename,
            max_size=LOGO_MAX_SIZE,
            thumbnails=LOGO_SIZES,
        ),
        show_as_ref=True,
        thumbnail_info={
            "size": BIGGEST_LOGO_SIZE,
        },
    )
    business_number_id = field(StringField(max_length=ORG_BID_SIZE_LIMIT), checks=[check_siret])

    members = field(ListField(EmbeddedDocumentField(Member)), readonly=True)
    teams = field(ListField(EmbeddedDocumentField(Team)), readonly=True)
    requests = field(ListField(EmbeddedDocumentField(MembershipRequest)), readonly=True)

    ext = field(MapField(GenericEmbeddedDocumentField()), readonly=True)
    zone = field(StringField(), readonly=True)
    extras = field(OrganizationExtrasField(), auditable=False)

    deleted = field(DateTimeField(), readonly=True)

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

    verbose_name = _("organization")

    def __str__(self):
        return self.name or ""

    @property
    @field(nested_fields=org_permissions_fields, show_as_ref=True)
    def permissions(self):
        from .permissions import EditOrganizationPermission, OrganizationPrivatePermission

        return {
            "edit": EditOrganizationPermission(self),
            "delete": EditOrganizationPermission(self),
            "members": EditOrganizationPermission(self),
            "harvest": EditOrganizationPermission(self),
            "private": OrganizationPrivatePermission(self),
        }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compute_aggregate_metrics = True

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    def self_web_url(self, **kwargs):
        return cdata_url(f"/organizations/{self._link_id(**kwargs)}", **kwargs)

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
            if (
                request.user == user
                and request.status == "pending"
                and request.kind != "invitation"
            ):
                return request
        return None

    @field(description="Link to the API endpoint for this organization", show_as_ref=True)
    def uri(self, *args, **kwargs):
        return self.self_api_url(*args, **kwargs)

    @field(description="Link to the udata web page for this organization", show_as_ref=True)
    def page(self, *args, **kwargs):
        return self.self_web_url(*args, **kwargs)

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

    def add_membership_request(self, membership_request):
        self.requests.append(membership_request)
        self.save()
        MembershipRequest.after_create.send(membership_request, org=self)

    def create_invitation(
        self,
        invited_by,
        user=None,
        email=None,
        role=DEFAULT_ROLE,
        comment=None,
        assignment_subjects=None,
    ):
        """Create a membership invitation after validating constraints.

        Either user or email must be provided, not both.
        Raises FieldValidationError on validation failure.
        """
        if user and email:
            raise FieldValidationError(field="user", message="Cannot provide both user and email")
        if not user and not email:
            raise FieldValidationError(field="user", message="Either user or email is required")

        if email:
            from udata.core.contact_point.models import check_is_email

            check_is_email(email, field="email")

        if role not in ORG_ROLES:
            raise FieldValidationError(field="role", message=f"Invalid role '{role}'")

        # Resolve email to existing user
        if email and not user:
            from udata.core.user.models import User

            user = User.objects(email=email.lower()).first()
            if user:
                email = None

        # Check duplicates
        email_lower = email.lower() if email else None
        for member in self.members:
            if user and member.user == user:
                raise FieldValidationError(field="user", message="User is already a member")
        for req in self.requests:
            if req.status != "pending":
                continue
            if user and req.user == user:
                raise FieldValidationError(
                    field="user", message="A request or invitation is already pending for this user"
                )
            if email_lower and req.email and req.email.lower() == email_lower:
                raise FieldValidationError(
                    field="email", message="An invitation is already pending for this email"
                )

        # Validate assignments
        if assignment_subjects and role != "partial_editor":
            raise FieldValidationError(
                field="assignments",
                message="Assignments can only be set for partial_editor role",
            )

        invitation = MembershipRequest(
            kind="invitation",
            user=user,
            email=email_lower,
            created_by=invited_by,
            role=role,
            comment=comment,
            assignments=assignment_subjects or [],
        )
        self.requests.append(invitation)
        self.save()
        MembershipRequest.after_create.send(invitation, org=self)
        return invitation

    def count_members(self):
        self.metrics["members"] = len(self.members)
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_datasets(self):
        from udata.models import Dataset, Follow, Reuse

        self.metrics["datasets"] = Dataset.objects(organization=self).visible().count()
        if self.compute_aggregate_metrics:
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
