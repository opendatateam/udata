# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import slugify

from flask.ext.mongoengine import Document
from mongoengine.fields import StringField
from mongoengine.signals import pre_save

log = logging.getLogger(__name__)


class SlugField(StringField):
    '''
    A field that that produces a slug from the inputs and auto-
    increments the slug if the value already exists.
    '''
    def __init__(self, populate_from=None, update=False, lower_case=True, separator='-', follow=False, **kwargs):
        kwargs.setdefault('unique', True)
        self.populate_from = populate_from
        self.update = update
        self.lower_case = lower_case
        self.separator = separator
        self.follow = follow
        self.old_value = None
        self.new_value = None
        super(SlugField, self).__init__(**kwargs)

    def __set__(self, instance, value):
        '''Store the previous value'''
        old_value = getattr(instance, self.db_field)
        if old_value != value:
            self.old_value = old_value
            self.new_value = value
        return super(SlugField, self).__set__(instance, value)

    def clear(self):
        self.old_value = None
        self.new_value = None


class SlugFollow(Document):
    '''
    Keeps track of slug changes for a given namespace/class.
    Fields are:
        * namespace - A namespace under which this slug falls (e.g. match, team, user etc)
        * old_slug - Before change slug.
        * new_slug - After change slug
    '''
    namespace = StringField()
    old_slug = StringField()
    new_slug = StringField()            # In case slug was changed after a name change.

    meta = {
        "indexes": [
            ("namespace", "old_slug"),
        ]
    }


def populate_slug(instance, field):
    '''
    Populate a slug field if needed.
    '''
    if not field.populate_from and not field.new_value:
        return

    if field.new_value:
        value = field.new_value
    elif callable(field.populate_from):
        value = field.populate_from(instance)
    else:
        value = getattr(instance, field.populate_from)

    if field.lower_case:
        value = value.lower()

    slug = slugify.slugify(value, max_length=field.max_length, separator=field.separator)

    # Do nothing if unchanged
    old_slug = field.old_value or getattr(instance, field.db_field)
    if slug == old_slug or (not field.update and old_slug):
        field.clear()
        return

    # Ensure uniqueness
    if field.unique:
        base_slug = slug
        index = 1
        qs = instance.__class__.objects
        exists = lambda s: qs(class_check=False, **dict([(field.db_field, s)])).first()
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
    field.clear()


@pre_save.connect
def check_slug_fields(sender, document):
    '''Populate slug fields before saving models'''
    for name, field in document._fields.items():
        if isinstance(field, SlugField):
            populate_slug(document, field)
