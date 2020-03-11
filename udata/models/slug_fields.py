import logging
import slugify

from flask_mongoengine import Document
from mongoengine.fields import StringField
from mongoengine.signals import pre_save, post_delete

from .queryset import UDataQuerySet
from udata.utils import is_uuid

log = logging.getLogger(__name__)


class SlugField(StringField):
    '''
    A field that that produces a slug from the inputs and auto-
    increments the slug if the value already exists.
    '''
    # Do not remove, this is required to trigger field population
    _auto_gen = True

    def __init__(self, populate_from=None, update=False, lower_case=True,
                 separator='-', follow=False, **kwargs):
        kwargs.setdefault('unique', True)
        self.populate_from = populate_from
        self.update = update
        self.lower_case = lower_case
        self.separator = separator
        self.follow = follow
        self.instance = None
        super(SlugField, self).__init__(**kwargs)

    def __get__(self, instance, owner):
        # mongoengine calls this after document initialization
        # We register signals handlers here to have a owner reference
        if not hasattr(self, 'owner'):
            self.owner = owner
            pre_save.connect(self.populate_on_pre_save, sender=owner)
            if self.follow:
                post_delete.connect(self.cleanup_on_delete, sender=owner)
        return super(SlugField, self).__get__(instance, owner)

    def __deepcopy__(self, memo):
        # Fixes no_dereference by avoiding deep copying instance attribute
        copied = self.__class__()
        copied.__dict__.update(self.__dict__)
        return copied

    # Do not remove, this is required when field population is triggered
    def generate(self):
        pass

    def slugify(self, value):
        '''
        Apply slugification according to specified field rules
        '''
        if value is None:
            return

        return slugify.slugify(value, max_length=self.max_length,
                               separator=self.separator,
                               to_lower=self.lower_case)

    def latest(self, value):
        '''
        Get the latest object for a given old slug
        '''
        namespace = self.owner_document.__name__
        follow = SlugFollow.objects(namespace=namespace, old_slug=value).first()
        if follow:
            return self.owner_document.objects(slug=follow.new_slug).first()
        return None

    def cleanup_on_delete(self, sender, document, **kwargs):
        '''
        Clean up slug redirections on object deletion
        '''
        if not self.follow or sender is not self.owner_document:
            return
        slug = getattr(document, self.db_field)
        namespace = self.owner_document.__name__
        SlugFollow.objects(namespace=namespace, new_slug=slug).delete()

    def populate_on_pre_save(self, sender, document, **kwargs):
        field = document._fields.get(self.name)
        if field:
            populate_slug(document, field)


class SlugFollow(Document):
    '''
    Keeps track of slug changes for a given namespace/class.
    Fields are:
        * namespace - A namespace under which this slug falls
            (e.g. match, team, user etc)
        * old_slug - Before change slug.
        * new_slug - After change slug
    '''
    namespace = StringField(required=True)
    old_slug = StringField(required=True)
    new_slug = StringField(required=True)

    meta = {
        'indexes': [
            ('namespace', 'old_slug'),
        ],
        'queryset_class': UDataQuerySet,
    }


def populate_slug(instance, field):
    '''
    Populate a slug field if needed.
    '''
    value = getattr(instance, field.db_field)

    try:
        previous = instance.__class__.objects.get(id=instance.id)
    except Exception:
        previous = None

    # Field value has changed
    changed = field.db_field in instance._get_changed_fields()
    # Field initial value has been manually set
    manual = not previous and value or changed

    if not manual and field.populate_from:
        # value to slugify is extracted from populate_from parameter
        value = getattr(instance, field.populate_from)
        if previous and value == getattr(previous, field.populate_from):
            return value

    if previous and getattr(previous, field.db_field) == value:
        # value is unchanged from DB
        return value

    if previous and not changed and not field.update:
        # Field is not manually set and slug should not update on change
        return value

    slug = field.slugify(value)

    # This can happen when serializing an object which does not contain
    # the properties used to generate the slug. Typically, when such
    # an object is passed to one of the Celery workers (see issue #20).
    if slug is None:
        return

    old_slug = getattr(previous, field.db_field, None)

    if slug == old_slug:
        return slug

    # Ensure uniqueness
    if field.unique:
        base_slug = slug
        index = 1
        qs = instance.__class__.objects
        if previous:
            qs = qs(id__ne=previous.id)

        def exists(s):
            return qs(
                class_check=False, **{field.db_field: s}
            ).limit(1).count(True) > 0

        while exists(slug):
            slug = '{0}-{1}'.format(base_slug, index)
            index += 1

        if is_uuid(slug):
            slug = '{0}-uuid'.format(slug)

    # Track old slugs for this class
    if field.follow and old_slug != slug:
        ns = instance.__class__.__name__
        # Destroy redirections from this new slug
        SlugFollow.objects(namespace=ns, old_slug=slug).delete()

        if old_slug:
            # Create a redirect for previous slug
            slug_follower, created = SlugFollow.objects.get_or_create(
                namespace=ns,
                old_slug=old_slug,
                auto_save=False,
            )
            slug_follower.new_slug = slug
            slug_follower.save()

            # Maintain previous redirects
            SlugFollow.objects(namespace=ns, new_slug=old_slug).update(new_slug=slug)

    setattr(instance, field.db_field, slug)
    return slug
