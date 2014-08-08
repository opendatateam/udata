# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import search

from udata.models import Post, Reuse, Dataset

from . import front, render


TAB_SIZE = 12


@front.route('/')
def home():
    # TODO:allow customization
    (
        recent_datasets,
        recent_reuses,
        featured_datasets,
        featured_reuses,
        popular_datasets,
        popular_reuses
    ) = search.multiquery(
        search.SearchQuery(Dataset, sort='-created', page_size=TAB_SIZE),
        search.SearchQuery(Reuse, sort='-created', page_size=TAB_SIZE),
        search.SearchQuery(Dataset, featured=True, page_size=3),
        search.SearchQuery(Reuse, featured=True, page_size=3),
        search.SearchQuery(Dataset, page_size=TAB_SIZE),
        search.SearchQuery(Reuse, page_size=TAB_SIZE),
    )

    return render('home.html',
        recent_datasets=recent_datasets,
        recent_reuses=recent_reuses,
        featured_datasets=featured_datasets,
        featured_reuses=featured_reuses,
        popular_datasets=popular_datasets,
        popular_reuses=popular_reuses,
        last_post=Post.objects(private=False).order_by('-created_at').first(),  # TODO extract into extension
    )
