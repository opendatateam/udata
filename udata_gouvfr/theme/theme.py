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
    'tab_size': 8,
    'home_datasets': [],
    'home_reuses': []
})


@theme.context('home')
def home_context(context):
    config = theme.current.config
    specs = {
        'recent_datasets': search.SearchQuery(Dataset, sort='-created', page_size=config['tab_size']),
        'recent_reuses': search.SearchQuery(Reuse, sort='-created', page_size=config['tab_size']),
        # 'featured_datasets': search.SearchQuery(Dataset, featured=True, page_size=3),
        'featured_reuses': search.SearchQuery(Reuse, featured=True, page_size=9),
        'popular_datasets': search.SearchQuery(Dataset, page_size=config['tab_size']),
        'popular_reuses': search.SearchQuery(Reuse, page_size=config['tab_size']),
    }
    keys, queries = zip(*specs.items())

    results = search.multiquery(*queries)

    context.update(zip(keys, results))
    context['last_post'] = Post.objects(private=False).order_by('-created_at').first()
    return context
