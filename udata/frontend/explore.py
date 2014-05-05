# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Dataset, Reuse

from . import front, render


@front.route('/explore/')
def explore():
    recent_datasets = list(Dataset.objects.visible().order_by('-date').limit(9))
    recent_reuses = list(Reuse.objects.order_by('-date').limit(9))
    featured_datasets = list(Dataset.objects(featured=True).visible().order_by('-date').limit(15))
    featured_reuses = list(Reuse.objects(featured=True).order_by('-date').limit(15))

    return render('explore.html',
        recent_datasets=recent_datasets,
        recent_reuses=recent_reuses,
        featured_datasets=featured_datasets,
        featured_reuses=featured_reuses,
    )
