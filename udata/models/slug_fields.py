# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import slugify

from flask_mongoengine import Document
from mongoengine.fields import StringField

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


class SlugFollow(Document):
    '''
    Keeps track of slug changes for a given namespace/class.
    Fields are:
        * namespace - A namespace under which this slug falls
            (e.g. match, team, user etc)
        * old_slug - Before change slug.
        * new_slug - After change slug
    '''
    namespace = StringField()
    old_slug = StringField()
    new_slug = StringField()  # In case slug was changed after a name change.

    meta = {
        "indexes": [
            ("namespace", "old_slug"),
        ]
    }


def populate_slug(instance, field):
    '''
    Populate a slug field if needed.
    '''
    value = getattr(instance, field.db_field)

    try:
        previous = instance.__class__.objects.get(id=instance.id)
    except:
        previous = None

    manual = (not previous and value or
              field.db_field in instance._get_changed_fields())

    if not manual and field.populate_from:
        value = getattr(instance, field.populate_from)
        if previous and value == getattr(previous, field.populate_from):
            return value

    if previous and (getattr(previous, field.db_field) == value or
                     not field.update):
        return value

    slug = field.slugify(value)

    # This can happen when serializing an object which does not contain
    # the properties used to generate the slug. Typically, when such
    # an object is passed to one of the Celery workers (see issue #20).
    if slug is None:
        return

    # If previous and slug ==
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
    if field.follow and slug != old_slug:
        slug_follower, created = SlugFollow.get_or_create(
            namespace=instance.__class__.__name__,
            old_slug=old_slug
        )

        slug_follower.new_slug = slug
        slug_follower.save()

    setattr(instance, field.db_field, slug)
    return slug
