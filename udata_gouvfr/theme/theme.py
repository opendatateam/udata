# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import re

import feedparser

from dateutil.parser import parse
from flask import g, current_app

from udata import search, theme
from udata.app import cache, nav
from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, Post


RE_POST_IMG = re.compile(r'\<img .* src="https?:(?P<src>.+\.(?:png|jpg))" .* />(?P<content>.+)')


@theme.admin_form
class GouvfrThemeForm(Form):
    tab_size = fields.IntegerField(_('Tab size'), description=_('Home page tab size'),
                                   validators=[validators.required()])
    atom_url = fields.StringField(_('ATOM Feed URL'),
                                  description=_('An optionnal atom feed URL for display blog post in home page'))

theme.defaults({
    'tab_size': 8,
    'home_datasets': [],
    'home_reuses': []
})


class Wikitem(nav.Item):
    def __init__(self, label, page, **kwargs):
        super(Wikitem, self).__init__(label, page.lower(), url='//wiki.data.gouv.fr/wiki/{0}'.format(page), **kwargs)


gouvfr_menu = nav.Bar('gouvfr_menu', [
    nav.Item(_('Discover OpenData'), 'gouvfr.faq', items=[
        nav.Item(_('As a citizen'), 'gouvfr.faq', {'section': 'citizen'}),
        nav.Item(_('As a producer'), 'gouvfr.faq', {'section': 'producer'}),
        nav.Item(_('As a reuser'), 'gouvfr.faq', {'section': 'reuser'}),
        nav.Item(_('As a developer'), 'gouvfr.faq', {'section': 'developer'}),
    ]),
    nav.Item(_('Data'), 'datasets.list', items=[
        nav.Item(_('Datasets'), 'datasets.list'),
        nav.Item(_('Reuses'), 'reuses.list'),
        nav.Item(_('Organizations'), 'organizations.list'),
    ]),
    nav.Item(_('Dashboard'), 'site.dashboard'),
    nav.Item(_('Événements'), '#', url='#', items=[
        nav.Item('Climate Change Challenge (C³)', 'gouvfr.c3'),
        nav.Item('Dataconnexions', 'gouvfr.dataconnexions'),
    ]),
    # nav.Item('Dataconnexions', 'gouvfr.dataconnexions'),
    nav.Item('Etalab', 'etalab', url='http://www.etalab.gouv.fr/'),
    nav.Item('CADA', 'cada', url='http://cada.data.gouv.fr/'),
])

theme.menu(gouvfr_menu)

nav.Bar('gouvfr_footer', [
    nav.Item(_('As a citizen'), 'gouvfr.faq', {'section': 'citizen'}),
    nav.Item(_('As a producer'), 'gouvfr.faq', {'section': 'producer'}),
    nav.Item(_('As a reuser'), 'gouvfr.faq', {'section': 'reuser'}),
    nav.Item(_('As a developer'), 'gouvfr.faq', {'section': 'developer'}),
    nav.Item(_('Credits'), 'gouvfr.credits'),
    nav.Item(_('Terms of use'), 'gouvfr.terms'),
])

NETWORK_LINKS = [
    ('Gouvernement.fr', 'http://www.gouvernement.fr'),
    ('France.fr', 'http://www.france.fr'),
    ('Legifrance.gouv.fr', 'http://www.legifrance.gouv.fr'),
    ('Service-public.fr', 'http://www.service-public.fr'),
    ('Opendata France', 'http://opendatafrance.net'),
    ('CADA.fr', 'http://www.cada.fr'),
    ('Etalab.gouv.fr', 'http://www.etalab.gouv.fr'),
]

nav.Bar('gouvfr_network', [nav.Item(label, label, url=url) for label, url in NETWORK_LINKS])


@cache.memoize(50)
def get_blog_post(url, lang):
    for code in lang, current_app.config['DEFAULT_LANGUAGE']:
        feed_url = url.format(lang=code)
        feed = feedparser.parse(feed_url)
        if len(feed['entries']) > 0:
            break
    if len(feed['entries']) <= 0:
        return None

    post = feed.entries[0]
    blogpost = {
        'title': post.title,
        'link': post.link,
        'date': parse(post.published)
    }
    match = RE_POST_IMG.match(post.content[0].value)
    if match:
        blogpost.update(image_url=match.group('src'), summary=match.group('content'))
    else:
        blogpost['summary'] = post.summary
    return blogpost


@theme.context('home')
def home_context(context):
    config = theme.current.config
    if 'atom_url' in config:
        context['blogpost'] = get_blog_post(config['atom_url'], g.lang_code)
    return context
