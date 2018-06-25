# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import slugify

from flask_mongoengine import Document
from mongoengine.fields import StringField
from mongoengine.signals import post_delete

from .queryset import UDataQuerySet

log = logging.getLogger(__name__)


class SlugField(StringField):
    '''
    A field that that produces a slug from the inputs and auto-
    increments the slug if the value already exists.
    '''
    _auto_gen = True

    def __init__(self, populate_from=None, update=False, lower_case=True,
                 separator='-', follow=False, **kwargs):
        kwargs.setdefault('unique', True)
        self.populate_from = populate_from
        self.update = update
        self.lower_case = lower_case
        self.separator = separator
        self.follow = follow
        super(SlugField, self).__init__(**kwargs)
        if follow:
            # Can't use sender=self.owner_document which is not yet defined
            post_delete.connect(self.cleanup_on_delete)

    def __get__(self, instance, owner):
        if instance is not None:
            self.instance = instance
        return super(SlugField, self).__get__(instance, owner)

    def __set__(self, instance, value):
        if instance is not None:
            self.instance = instance
        return super(SlugField, self).__set__(instance, value)

    def validate(self, value):
        populate_slug(self.instance, self)

    def generate(self):
        return populate_slug(self.instance, self)

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

    def cleanup_on_delete(self, sender, document):
        '''
        Clean up slug redirections on object deletion
        '''
        if not self.follow or sender is not self.owner_document:
            return
        slug = getattr(document, self.db_field)
        namespace = self.owner_document.__name__
        SlugFollow.objects(namespace=namespace, new_slug=slug).delete()


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
