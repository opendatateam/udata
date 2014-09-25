# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# from copy import deepcopy

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


class Wikitem(nav.Item):
    def __init__(self, label, page, **kwargs):
        super(Wikitem, self).__init__(label, page.lower(), url='//wiki.data.gouv.fr/wiki/{0}'.format(page), **kwargs)


gouvfr_menu = nav.Bar('gouvfr_menu', [
    Wikitem(_('How it works ?'), 'FAQ', items=[
        Wikitem(_('Publication guide'), 'Guide_de_publication'),
        Wikitem(_('Tools'), 'Outillage_pour_les_datavisualisations'),
        Wikitem(_('Open Licence'), 'Licence_Ouverte_/_Open_Licence'),
        nav.Item(_('API'), 'api.root')
    ]),
    nav.Item(_('Data'), 'datasets.list', items=[
        nav.Item(_('Reuses'), 'reuses.list'),
        nav.Item(_('Organizations'), 'organizations.list'),
    ]),
    nav.Item(_('Dashboard'), 'site.dashboard'),
    nav.Item('Etalab', 'etalab', url='http://www.etalab.gouv.fr/'),
    nav.Item('CADA', 'cada', url='http://cada.data.gouv.fr/'),
])

theme.menu(gouvfr_menu)

nav.Bar('gouvfr_footer', list(gouvfr_menu.items) + [
    nav.Item(_('Credits'), 'credits', url='//wiki.data.gouv.fr/wiki/Crédits'),
    nav.Item(_('Terms of use'), 'terms', url='//wiki.data.gouv.fr/wiki/Conditions_Générales_d\'Utilisation'),
])


NETWORK_LINKS = [
    ('Gouvernement.fr', 'http://www.gouvernement.fr'),
    ('France.fr', 'http://www.france.fr'),
    ('Legifrance.gouv.fr', 'http://www.legifrance.gouv.fr'),
    ('Service-public.fr', 'http://www.service-public.fr'),
    ('Opendata France', 'http://opendatafrance.net'),
    ('CADA.fr', 'http://www.cada.fr'),
]

nav.Bar('gouvfr_network', [nav.Item(label, label, url=url) for label, url in NETWORK_LINKS])


@theme.context('home')
def home_context(context):
    config = theme.current.config
    specs = {
        'recent_datasets': search.SearchQuery(Dataset, sort='-created', page_size=config['tab_size']),
        # 'recent_reuses': search.SearchQuery(Reuse, sort='-created', page_size=config['tab_size']),
        # 'featured_datasets': search.SearchQuery(Dataset, featured=True, page_size=3),
        'featured_reuses': search.SearchQuery(Reuse, featured=True, page_size=9),
        'popular_datasets': search.SearchQuery(Dataset, page_size=config['tab_size']),
        'popular_reuses': search.SearchQuery(Reuse, page_size=config['tab_size']),
    }
    keys, queries = zip(*specs.items())

    results = search.multiquery(*queries)

    context.update(zip(keys, results))
    context['recent_reuses'] = Reuse.objects(featured=True).visible().order_by('-created_at').limit(3)
    context['last_post'] = Post.objects(private=False).order_by('-created_at').first()
    return context
