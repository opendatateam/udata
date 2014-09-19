# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import search
from udata.forms import Form, fields, validators
from udata.frontend import theme, nav
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


gouvfr_menu = nav.Bar('gouvfr_menu', [
    nav.Item(_('How it works ?'), 'faq', url='//wiki.data.gouv.fr/wiki/FAQ'),
    nav.Item(_('Organizations'), 'organizations.list'),
    nav.Item(_('Open Licence'), 'license', url='//wiki.data.gouv.fr/wiki/Licence_Ouverte_/_Open_Licence'),
    nav.Item(_('Dashboard'), 'site.dashboard'),
    nav.Item('Etalab', 'etalab', url='http://www.etalab.gouv.fr/'),
    nav.Item('CADA', 'cada', url='http://cada.data.gouv.fr/'),
])

theme.menu(gouvfr_menu)


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
