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

# Wordpress ATOM timeout
WP_TIMEOUT = 5


gouvfr_menu = nav.Bar('gouvfr_menu', [
    nav.Item(_('Discover OpenData'), None, url='https://doc.data.gouv.fr'),
    nav.Item(_('Data'), 'datasets.list', items=[
        nav.Item(_('Datasets'), 'datasets.list'),
        nav.Item(_('Reuses'), 'reuses.list'),
        nav.Item(_('Organizations'), 'organizations.list'),
    ]),
    nav.Item(_('Dashboard'), 'site.dashboard'),
    # nav.Item(_('Territories'), 'territories.home'),
])

theme.menu(gouvfr_menu)

nav.Bar('gouvfr_footer', [
    nav.Item(_('Documentation'), None, url='https://doc.data.gouv.fr'),
    nav.Item(_('Reference Data'), 'gouvfr.spd'),
    nav.Item(_('Licences'), 'gouvfr.licences'),
    nav.Item(_('API'), 'apidoc.swaggerui'),
    nav.Item(_('Terms of use'), 'site.terms'),
    nav.Item(_('Tracking and privacy'), 'gouvfr.suivi'),
])

NETWORK_LINKS = [
    ('Gouvernement.fr', 'http://www.gouvernement.fr'),
    ('France.fr', 'http://www.france.fr'),
    ('Legifrance.gouv.fr', 'http://www.legifrance.gouv.fr'),
    ('Service-public.fr', 'http://www.service-public.fr'),
    ('Opendata France', 'http://opendatafrance.net'),
    ('CADA.fr', 'http://www.cada.fr'),
    ('Etalab.gouv.fr', 'https://www.etalab.gouv.fr'),
]

nav.Bar(
    'gouvfr_network',
    [nav.Item(label, label, url=url) for label, url in NETWORK_LINKS]
)


@cache.memoize(50)
def get_blog_post(lang):
    wp_atom_url = current_app.config.get('WP_ATOM_URL')
    if not wp_atom_url:
        return

    feed = None

    for code in lang, current_app.config['DEFAULT_LANGUAGE']:
        feed_url = wp_atom_url.format(lang=code)
        try:
            response = requests.get(feed_url, timeout=WP_TIMEOUT)
        except requests.Timeout:
            log.error('Timeout while fetching %s', feed_url, exc_info=True)
            continue
        except requests.RequestException:
            log.error('Error while fetching %s', feed_url, exc_info=True)
            continue
        feed = feedparser.parse(response.content)
        if len(feed.entries) > 0:
            break

    if not feed or len(feed.entries) <= 0:
        return

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


def _discourse_request(url):
    """Helper for discourse requests"""
    timeout = current_app.config.get('DISCOURSE_TIMEOUT', 15)
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException:
        log.exception('Unable to fetch discourse content for url %s' % url)
        return
    except requests.exceptions.Timeout:
        log.exception('Timeout while fetching discourse url %s' % url)
        return
    try:
        return response.json()
    except ValueError:
        log.exception('Unable to parse discourse JSON for url %s' % url)
        return


@cache.cached(50)
def get_discourse_posts():
    base_url = current_app.config.get('DISCOURSE_URL')
    category_id = current_app.config.get('DISCOURSE_CATEGORY_ID')
    listing = current_app.config.get('DISCOURSE_LISTING_TYPE', 'latest')
    limit = current_app.config.get('DISCOURSE_LISTING_LIMIT', 5)
    if not base_url:
        return

    # Fetch site wide configuration (including all categories labels)
    site_url = '{url}/site.json'.format(url=base_url)
    data = _discourse_request(site_url)
    if not data:
        return

    # Resolve categories names
    categories = {}
    for category in data['categories']:
        categories[category['id']] = category['name']

    # Fetch last topic from selected category (if any)
    pattern = '{url}/l/{listing}.json'
    if category_id:
        pattern = '{url}/c/{category}/l/{listing}.json'
        # return topics
    url = pattern.format(url=base_url,
                         category=category_id,
                         listing=listing)
    data = _discourse_request(url)
    if not data:
        return

    # Resolve posters avatars
    users = {}
    for user in data['users']:
        users[user['id']] = {
            'id': user['id'],
            'name': user['username'],
            'avatar_url': '{0}{1}'.format(base_url, user['avatar_template'])
        }

    # Parse topics
    topics = []
    topic_pattern = '{url}/t/{slug}/{id}'
    for topic in data['topic_list']['topics'][:limit]:
        last_posted = topic['last_posted_at']
        last_posted = parse(last_posted) if last_posted else None
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
            'last_posted_at': last_posted,
            'posters': [
                users[u['user_id']] for u in topic['posters']
            ]
        })

    return topics


@theme.context('home')
def home_context(context):
    context['blogpost'] = get_blog_post(g.lang_code)
    context['forum_topics'] = get_discourse_posts()
    return context
