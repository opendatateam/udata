from datetime import datetime
from itertools import chain

from blinker import Signal
from flask import url_for
from mongoengine.signals import pre_save, post_save
from werkzeug import cached_property
from elasticsearch_dsl import Integer, Object

from udata.core.storages import avatars, default_image_basename
from udata.frontend.markdown import mdstrip
from udata.models import db, BadgeMixin, WithMetrics
from udata.i18n import lazy_gettext as _
from udata.uris import endpoint_for


__all__ = (
    'Organization', 'Team', 'Member', 'MembershipRequest',
    'ORG_ROLES', 'MEMBERSHIP_STATUS', 'PUBLIC_SERVICE', 'CERTIFIED'
)


ORG_ROLES = {
    'admin': _('Administrator'),
    'editor': _('Editor'),
}
DEFAULT_ROLE = 'editor'


MEMBERSHIP_STATUS = {
    'pending': _('Pending'),
    'accepted': _('Accepted'),
    'refused': _('Refused'),
}

LOGO_MAX_SIZE = 500
LOGO_SIZES = [100, 60, 25]

PUBLIC_SERVICE = 'public-service'
CERTIFIED = 'certified'

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000


class Team(db.EmbeddedDocument):
    name = db.StringField(required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from='name', update=True,
        unique=False)
    description = db.StringField()

    members = db.ListField(db.ReferenceField('User'))


class Member(db.EmbeddedDocument):
    user = db.ReferenceField('User')
    role = db.StringField(choices=list(ORG_ROLES), default=DEFAULT_ROLE)
    since = db.DateTimeField(default=datetime.now, required=True)

    @property
    def label(self):
        return ORG_ROLES[self.role]


class MembershipRequest(db.EmbeddedDocument):
    '''
    Pending organization membership requests
    '''
    id = db.AutoUUIDField()
    user = db.ReferenceField('User')
    status = db.StringField(
        choices=list(MEMBERSHIP_STATUS), default='pending')

    created = db.DateTimeField(default=datetime.now, required=True)

    handled_on = db.DateTimeField()
    handled_by = db.ReferenceField('User')

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


class Organization(WithMetrics, BadgeMixin, db.Datetimed, db.Document):
    name = db.StringField(required=True)
    acronym = db.StringField(max_length=128)
    slug = db.SlugField(max_length=255, required=True, populate_from='name',
                        update=True, follow=True)
    description = db.StringField(required=True)
    url = db.StringField()
    image_url = db.StringField()
    logo = db.ImageField(fs=avatars, basename=default_image_basename,
                         max_size=LOGO_MAX_SIZE, thumbnails=LOGO_SIZES)

    members = db.ListField(db.EmbeddedDocumentField(Member))
    teams = db.ListField(db.EmbeddedDocumentField(Team))
    requests = db.ListField(db.EmbeddedDocumentField(MembershipRequest))

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    zone = db.StringField()
    extras = db.ExtrasField()

    deleted = db.DateTimeField()

    meta = {
        'indexes': ['-created_at', 'slug'],
        'ordering': ['-created_at'],
        'queryset_class': OrganizationQuerySet,
    }

    def __str__(self):
        return self.name or ''

    __badges__ = {
        PUBLIC_SERVICE: _('Public Service'),
        CERTIFIED: _('Certified'),
    }

    __search_metrics__ = Object(properties={
        'datasets': Integer(),
        'reuses': Integer(),
        'followers': Integer(),
        'views': Integer(),
    })

    __metrics_keys__ = [
        'datasets',
        'members',
        'reuses',
        'followers',
        'views',
    ]

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)

    def url_for(self, *args, **kwargs):
        return endpoint_for('organizations.show', 'api.organization', org=self, *args, **kwargs)

    display_url = property(url_for)

    @property
    def external_url(self):
        return self.url_for(_external=True)

    @property
    def pending_requests(self):
        return [r for r in self.requests if r.status == 'pending']

    @property
    def refused_requests(self):
        return [r for r in self.requests if r.status == 'refused']

    @property
    def accepted_requests(self):
        return [r for r in self.requests if r.status == 'accepted']

    @property
    def certified(self):
        return any(b.kind == CERTIFIED for b in self.badges)

    @property
    def public_service(self):
        is_public_service = any(b.kind == PUBLIC_SERVICE for b in self.badges)
        return self.certified and is_public_service

    def member(self, user):
        for member in self.members:
            if member.user == user:
                return member
        return None

    def is_member(self, user):
        return self.member(user) is not None

    def is_admin(self, user):
        member = self.member(user)
        return member is not None and member.role == 'admin'

    def pending_request(self, user):
        for request in self.requests:
            if request.user == user and request.status == 'pending':
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
            *[dataset.check_availability()
              for dataset in Dataset.objects(organization=self).visible()[:20]]
        )

    @cached_property
    def json_ld(self):
        type_ = 'GovernmentOrganization' if self.public_service \
                else 'Organization'

        result = {
            '@context': 'http://schema.org',
            '@type': type_,
            '@id': str(self.id),
            'alternateName': self.slug,
            'url': endpoint_for('organizations.show', 'api.organization', org=self, _external=True),
            'name': self.name,
            'dateCreated': self.created_at.isoformat(),
            'dateModified': self.last_modified.isoformat()
        }

        if self.description:
            result['description'] = mdstrip(self.description)

        logo = self.logo(external=True)
        if logo:
            result['logo'] = logo

        return result

    @property
    def views_count(self):
        return self.metrics.get('views', 0)

    def count_members(self):
        self.metrics['members'] = len(self.members)
        self.save()

    def count_datasets(self):
        from udata.models import Dataset
        self.metrics['datasets'] = Dataset.objects(organization=self).visible().count()
        self.save()

    def count_reuses(self):
        from udata.models import Reuse
        self.metrics['reuses'] = Reuse.objects(organization=self).count()
        self.save()

    def count_followers(self):
        from udata.models import Follow
        self.metrics['followers'] = Follow.objects(until=None).followers(self).count()
        self.save()


pre_save.connect(Organization.pre_save, sender=Organization)
post_save.connect(Organization.post_save, sender=Organization)
