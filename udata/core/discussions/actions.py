# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse, Dataset

from .models import Discussion


def discussions_for(user, closed=False):
    '''
    Build a queryset to query discussions related to a given user's assets.

    It includes discussions coming from the user's organizations

    :param bool closed: whether to include closed discussions or not.
    '''
    orgs = [o for o in user.organizations if o.is_member(user)]
    datasets = Dataset.objects.owned_by(user.id, *orgs)
    reuses = Reuse.objects.owned_by(user.id, *orgs)

    qs = Discussion.objects(subject__in=list(datasets) + list(reuses))
    if not closed:
        qs = qs(closed__exists=False)
    return qs
