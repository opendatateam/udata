# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from blinker import signal
from mongoengine import NULLIFY, Q, pre_save, post_save
from mongoengine.fields import ReferenceField

from .queryset import UDataQuerySet

log = logging.getLogger(__name__)


class OwnedQuerySet(UDataQuerySet):
    def owned_by(self, *owners):
        qs = Q()
        for owner in owners:
            qs |= Q(owner=owner) | Q(organization=owner)
        return self(qs)


class Owned(object):
    '''
    A mixin to factorize owning behvaior between users and organizations.
    '''
    owner = ReferenceField('User', reverse_delete_rule=NULLIFY)
    organization = ReferenceField('Organization', reverse_delete_rule=NULLIFY)

    on_owner_change = signal('Owned.on_owner_change')

    meta = {
        'indexes': [
            'owner',
            'organization',
        ],
        'queryset_class': OwnedQuerySet,
    }


def owned_pre_save(sender, document, **kwargs):
    '''
    Owned mongoengine.pre_save signal handler
    Need to fetch original owner before the new one erase it.
    '''
    if not isinstance(document, Owned):
        return
    changed_fields = getattr(document, '_changed_fields', [])
    if 'organization' in changed_fields:
        if document.owner:
            # Change from owner to organization
            document._previous_owner = document.owner
            document.owner = None
        else:
            # Change from org to another
            # Need to fetch previous value in base
            original = sender.objects.only('organization').get(pk=document.pk)
            document._previous_owner = original.organization
    elif 'owner' in changed_fields:
        if document.organization:
            # Change from organization to owner
            document._previous_owner = document.organization
            document.organization = None
        else:
            # Change from owner to another
            # Need to fetch previous value in base
            original = sender.objects.only('owner').get(pk=document.pk)
            document._previous_owner = original.owner


def owned_post_save(sender, document, **kwargs):
    '''
    Owned mongoengine.post_save signal handler
    Dispatch the `Owned.on_owner_change` signal
    once the document has been saved including the previous owner.

    The signal handler should have the following signature:
    ``def handler(document, previous)``
    '''
    if isinstance(document, Owned) and hasattr(document, '_previous_owner'):
        Owned.on_owner_change.send(document, previous=document._previous_owner)


pre_save.connect(owned_pre_save)
post_save.connect(owned_post_save)
