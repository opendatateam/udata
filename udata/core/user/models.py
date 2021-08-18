from copy import copy
from datetime import datetime
from itertools import chain
from time import time

from blinker import Signal
from flask import current_app
from flask_security import UserMixin, RoleMixin, MongoEngineUserDatastore
from mongoengine.signals import pre_save, post_save
from itsdangerous import JSONWebSignatureSerializer
from elasticsearch_dsl import Integer, Object

from werkzeug import cached_property

from udata import mail
from udata.uris import endpoint_for
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.models import db, WithMetrics, Follow
from udata.core.discussions.models import Discussion
from udata.core.storages import avatars, default_image_basename

__all__ = ('User', 'Role', 'datastore')

AVATAR_SIZES = [500, 200, 100, 32, 25]


# TODO: use simple text for role
class Role(db.Document, RoleMixin):
    ADMIN = 'admin'
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)

    def __str__(self):
        return self.name


class UserSettings(db.EmbeddedDocument):
    prefered_language = db.StringField()


class User(WithMetrics, UserMixin, db.Document):
    slug = db.SlugField(
        max_length=255, required=True, populate_from='fullname')
    email = db.StringField(max_length=255, required=True, unique=True)
    password = db.StringField()
    active = db.BooleanField()
    roles = db.ListField(db.ReferenceField(Role), default=[])

    first_name = db.StringField(max_length=255, required=True)
    last_name = db.StringField(max_length=255, required=True)

    avatar_url = db.URLField()
    avatar = db.ImageField(
        fs=avatars, basename=default_image_basename, thumbnails=AVATAR_SIZES)
    website = db.URLField()
    about = db.StringField()

    prefered_language = db.StringField()

    apikey = db.StringField()

    created_at = db.DateTimeField(default=datetime.now, required=True)

    # The field below is required for Flask-security
    # when SECURITY_CONFIRMABLE is True
    confirmed_at = db.DateTimeField()

    password_rotation_demanded = db.DateTimeField()
    password_rotation_performed = db.DateTimeField()

    # The 5 fields below are required for Flask-security
    # when SECURITY_TRACKABLE is True
    last_login_at = db.DateTimeField()
    current_login_at = db.DateTimeField()
    last_login_ip = db.StringField()
    current_login_ip = db.StringField()
    login_count = db.IntField()

    deleted = db.DateTimeField()
    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    meta = {
        'indexes': ['-created_at', 'slug', 'apikey'],
        'ordering': ['-created_at']
    }

    __search_metrics__ = Object(properties={
        'datasets': Integer(),
        'reuses': Integer(),
        'followers': Integer(),
        'views': Integer()
    })

    __metrics_keys__ = [
        'datasets',
        'reuses',
        'following',
        'followers',
    ]

    def __str__(self):
        return self.fullname

    @property
    def fullname(self):
        return ' '.join((self.first_name or '', self.last_name or '')).strip()

    @cached_property
    def organizations(self):
        from udata.core.organization.models import Organization
        return Organization.objects(members__user=self, deleted__exists=False)

    @property
    def sysadmin(self):
        return self.has_role('admin')

    def url_for(self, *args, **kwargs):
        return endpoint_for('users.show', 'api.user', user=self, *args, **kwargs)

    display_url = property(url_for)

    @property
    def external_url(self):
        return self.url_for(_external=True)

    @property
    def visible(self):
        count = self.metrics.get('datasets', 0) + self.metrics.get('reuses', 0)
        return count > 0 and self.active

    @cached_property
    def resources_availability(self):
        """Return the percentage of availability for resources."""
        # Flatten the list.
        availabilities = list(
            chain(
                *[org.check_availability() for org in self.organizations]
            )
        )
        # Filter out the unknown
        availabilities = [a for a in availabilities if type(a) is bool]
        if availabilities:
            # Trick will work because it's a sum() of booleans.
            return round(100. * sum(availabilities) / len(availabilities), 2)
        # if nothing is unavailable, everything is considered OK
        return 100

    @cached_property
    def datasets_org_count(self):
        """Return the number of datasets of user's organizations."""
        from udata.models import Dataset  # Circular imports.
        return sum(Dataset.objects(organization=org).visible().count()
                   for org in self.organizations)

    @cached_property
    def followers_org_count(self):
        """Return the number of followers of user's organizations."""
        from udata.models import Follow  # Circular imports.
        return sum(Follow.objects(following=org).count()
                   for org in self.organizations)

    @property
    def datasets_count(self):
        """Return the number of datasets of the user."""
        return self.metrics.get('datasets', 0)

    @property
    def followers_count(self):
        """Return the number of followers of the user."""
        return self.metrics.get('followers', 0)

    def generate_api_key(self):
        s = JSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        byte_str = s.dumps({
            'user': str(self.id),
            'time': time(),
        })
        self.apikey = byte_str.decode()

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
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)

    @cached_property
    def json_ld(self):

        result = {
            '@type': 'Person',
            '@context': 'http://schema.org',
            'name': self.fullname,
        }

        if self.about:
            result['description'] = mdstrip(self.about)

        if self.avatar_url:
            result['image'] = self.avatar_url

        if self.website:
            result['url'] = self.website

        return result

    def _delete(self, *args, **kwargs):
        return db.Document.delete(self, *args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError('''This method should not be using directly.
        Use `mark_as_deleted` (or `_delete` if you know what you're doing)''')

    def mark_as_deleted(self):
        copied_user = copy(self)
        self.email = '{}@deleted'.format(self.id)
        self.slug = 'deleted'
        self.password = None
        self.active = False
        self.first_name = 'DELETED'
        self.last_name = 'DELETED'
        self.avatar = None
        self.avatar_url = None
        self.website = None
        self.about = None
        self.extras = None
        self.apikey = None
        self.deleted = datetime.now()
        self.save()
        for organization in self.organizations:
            organization.members = [member
                                    for member in organization.members
                                    if member.user != self]
            organization.save()
        for discussion in Discussion.objects(discussion__posted_by=self):
            for message in discussion.discussion:
                if message.posted_by == self:
                    message.content = 'DELETED'
            discussion.save()
        Follow.objects(follower=self).delete()
        Follow.objects(following=self).delete()
        mail.send(_('Account deletion'), copied_user, 'account_deleted')

    def count_datasets(self):
        from udata.models import Dataset
        self.metrics['datasets'] = Dataset.objects(owner=self).visible().count()
        self.save()

    def count_reuses(self):
        from udata.models import Reuse
        self.metrics['reuses'] = Reuse.objects(owner=self).visible().count()
        self.save()

    def count_followers(self):
        from udata.models import Follow
        self.metrics['followers'] = Follow.objects(until=None).followers(self).count()
        self.save()

    def count_following(self):
        from udata.models import Follow
        self.metrics['following'] = Follow.objects.following(self).count()
        self.save()


datastore = MongoEngineUserDatastore(db, User, Role)

pre_save.connect(User.pre_save, sender=User)
post_save.connect(User.post_save, sender=User)
