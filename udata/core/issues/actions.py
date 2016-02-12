# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse, Dataset

from .models import Issue


def issues_for(user, only_open=True):
    '''
    Build a queryset to query issues for a given user's assets.

    It includes issues coming from the user's organizations

    :param bool only_open: whether to include closed issues or not.
    '''
    datasets = Dataset.objects.owned_by(user.id, *user.organizations)
    reuses = Reuse.objects.owned_by(user.id, *user.organizations)

    qs = Issue.objects(subject__in=list(datasets) + list(reuses))
    if only_open:
        qs = qs(closed__exists=False)
    return qs
