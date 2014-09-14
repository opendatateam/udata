# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import search
from udata.forms import Form, fields, validators
from udata.frontend import theme
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, Post


@theme.admin_form
class GouvfrThemeForm(Form):
    tab_size = fields.IntegerField(_('Tab size'), description=_('Home page tab size'),
        validators=[validators.required()])

theme.defaults({
    'tab_size': 8
})


@theme.home_context
def home_context(theme):
    (
        recent_datasets,
        recent_reuses,
        featured_datasets,
        featured_reuses,
        popular_datasets,
        popular_reuses
    ) = search.multiquery(
        search.SearchQuery(Dataset, sort='-created', page_size=theme.config['tab_size']),
        search.SearchQuery(Reuse, sort='-created', page_size=theme.config['tab_size']),
        search.SearchQuery(Dataset, featured=True, page_size=3),
        search.SearchQuery(Reuse, featured=True, page_size=3),
        search.SearchQuery(Dataset, page_size=theme.config['tab_size']),
        search.SearchQuery(Reuse, page_size=theme.config['tab_size']),
    )
    return {
        'recent_datasets': recent_datasets,
        'recent_reuses': recent_reuses,
        'featured_datasets': featured_datasets,
        'featured_reuses': featured_reuses,
        'popular_datasets': popular_datasets,
        'popular_reuses': popular_reuses,
        'last_post': Post.objects(private=False).order_by('-created_at').first(),  # TODO extract into extension
    }
