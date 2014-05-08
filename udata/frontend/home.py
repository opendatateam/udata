# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.search import multiquery, DatasetSearch, ReuseSearch, SearchQuery

from udata.models import Post

from . import front, render


TAB_SIZE = 6


@front.route('/')
def home():
    # TODO:allow customization
    recent_datasets, recent_reuses, featured_datasets, featured_reuses, popular_datasets, popular_reuses = multiquery(
        SearchQuery(DatasetSearch, sort='-created_at', page_size=TAB_SIZE),
        SearchQuery(ReuseSearch, sort='-created_at', page_size=TAB_SIZE),
        SearchQuery(DatasetSearch, featured=True, page_size=3),
        SearchQuery(ReuseSearch, featured=True, page_size=3),
        SearchQuery(DatasetSearch, page_size=TAB_SIZE),
        SearchQuery(ReuseSearch, page_size=TAB_SIZE),
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
