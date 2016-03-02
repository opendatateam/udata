# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import re

import feedparser
import requests

from dateutil.parser import parse
from flask import g, current_app

from udata import theme
from udata.app import cache, nav
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

RE_POST_IMG = re.compile(
    r'\<img .* src="https?:(?P<src>.+\.(?:png|jpg))" .* />(?P<content>.+)')


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
    nav.Item(_('Events'), '#', url='#', items=[
        nav.Item('Nec Mergitur', 'gouvfr.nec_mergitur'),
        nav.Item('Climate Change Challenge (C³)',
                 'gouvfr.climate_change_challenge'),
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
    nav.Item(_('API'), 'apidoc.swaggerui'),
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

nav.Bar(
    'gouvfr_network',
    [nav.Item(label, label, url=url) for label, url in NETWORK_LINKS]
)


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
        blogpost.update(image_url=match.group('src'),
                        summary=match.group('content'))
    else:
        blogpost['summary'] = post.summary
    return blogpost


@cache.cached(50)
def get_discourse_posts():
    topics = []
    base_url = current_app.config.get('DISCOURSE_URL')
    category_id = current_app.config.get('DISCOURSE_CATEGORY_ID')
    listing = current_app.config.get('DISCOURSE_LISTING_TYPE', 'latest')
    limit = current_app.config.get('DISCOURSE_LISTING_LIMIT', 5)
    if not base_url:
        return topics

    # Fetch site wide configuration (including all categories labels)
    site_url = '{url}/site.json'.format(url=base_url)
    try:
        response = requests.get(site_url)
    except requests.exceptions.RequestException:
        log.exception('Unable to fetch discourses categories')
        return topics
    data = response.json()

    # Resolve categories names
    categories = {}
    for category in data['categories']:
        categories[category['id']] = category['name']

    # Fetch last topic from selected category (if any)
    pattern = '{url}/l/{listing}.json?limit={limit}'
    if category_id:
        pattern = '{url}/c/{category}/l/{listing}.json?limit={limit}'
        # return topics
    url = pattern.format(url=base_url,
                         category=category_id,
                         listing=listing,
                         limit=limit)
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException:
        log.exception('Unable to fetch discourses topics')
        return topics
    data = response.json()

    # Resolve posters avatars
    users = {}
    for user in data['users']:
        users[user['id']] = {
            'id': user['id'],
            'name': user['username'],
            'avatar_url': '{0}{1}'.format(base_url, user['avatar_template'])
        }

    # Parse topics
    topic_pattern = '{url}/t/{slug}/{id}'
    for topic in data['topic_list']['topics']:
        last_posted_at = topic['last_posted_at']
        topics.append({
            'id': topic['id'],
            'title': topic['title'],
            'fancy_title': topic['fancy_title'],
            'slug': topic['slug'],
            'url': topic_pattern.format(url=base_url, **topic),
            'category': categories[topic['category_id']],
            'posts': topic['posts_count'],
            'replies': topic['reply_count'],
            'likes': topic['like_count'],
            'views': topic['views'],
            'created_at': parse(topic['created_at']),
            'last_posted_at': parse(last_posted_at) if last_posted_at else None,
            'posters': [
                users[u['user_id']] for u in topic['posters']
            ]
        })

    return topics


@theme.context('home')
def home_context(context):
    config = theme.current.config
    if config and 'atom_url' in config:
        context['blogpost'] = get_blog_post(config['atom_url'], g.lang_code)
    context['forum_topics'] = get_discourse_posts()
    return context
