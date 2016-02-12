# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse, Dataset

from .models import Discussion


def discussions_for(user, only_open=True):
    '''
    Build a queryset to query discussions related to a given user's assets.

    It includes discussions coming from the user's organizations

    :param bool closed: whether to include closed discussions or not.
    '''
    datasets = Dataset.objects.owned_by(user.id, *user.organizations)
    reuses = Reuse.objects.owned_by(user.id, *user.organizations)

    qs = Discussion.objects(subject__in=list(datasets) + list(reuses))
    if only_open:
        qs = qs(closed__exists=False)
    return qs
