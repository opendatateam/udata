import logging
import re

import feedparser
import requests

from dateutil.parser import parse
from flask import g, current_app, url_for

from udata import theme
from udata.app import cache, nav
from udata.models import Dataset
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)

RE_POST_IMG = re.compile(
    r'''
    <img .*? (?:(?:
        src="(?P<src>https?://.+?)"
        |
        srcset="(?P<srcset>.+?)"
        |
        sizes="(?P<sizes>.+?)"
    )\s*)+ .*?/>
    ''',
    re.I | re.X | re.S
)

RE_STRIP_TAGS = re.compile(r'</?(img|br|p|div|ul|li|ol)[^<>]*?>', re.I | re.M)

# Add some html5 allowed attributes
EXTRA_ATTRIBUTES = ('srcset', 'sizes')
feedparser._HTMLSanitizer.acceptable_attributes.update(set(EXTRA_ATTRIBUTES))

# Wordpress ATOM timeout
WP_TIMEOUT = 5

# Feed allowed enclosure type as thumbnails
FEED_THUMBNAIL_MIMES = ('image/jpeg', 'image/png', 'image/webp')


gouvfr_menu = nav.Bar('gouvfr_menu', [
    nav.Item(_('Data'), 'datasets.list'),
    nav.Item(_('Reuses'), 'reuses.list'),
    nav.Item(_('Organizations'), 'organizations.list'),
    nav.Item(_('Dashboard'), 'site.dashboard'),
    nav.Item(_('Documentation'), None, url='https://doc.data.gouv.fr'),
])

theme.menu(gouvfr_menu)

footer_links = [
    nav.Item(_('Documentation'), None, url='https://doc.data.gouv.fr'),
    nav.Item(_('Reference Data'), 'gouvfr.spd'),
    nav.Item(_('Licences'), 'gouvfr.licences'),
    nav.Item(_('API'), None, url=current_app.config.get('API_DOC_EXTERNAL_LINK', '#')),
    nav.Item(_('Terms of use'), 'site.terms'),
    nav.Item(_('Tracking and privacy'), 'gouvfr.suivi'),
]

export_dataset_id = current_app.config.get('EXPORT_CSV_DATASET_ID')
if export_dataset_id:
    try:
        export_dataset = Dataset.objects.get(id=export_dataset_id)
    except Dataset.DoesNotExist:
        pass
    else:
        export_url = url_for('datasets.show', dataset=export_dataset,
                             _external=True)
        footer_links.append(nav.Item(_('Data catalog'), None, url=export_url))

footer_links.append(nav.Item('Données clés par sujet', 'gouvfr.show_page',
                             args={'slug': 'donnees-cles-par-sujet'}))

nav.Bar('gouvfr_footer', footer_links)

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
    '''
    Extract the latest post summary from an RSS or an Atom feed.

    Image is searched and extracted from (in order of priority):
      - mediarss `media:thumbnail` attribute
      - enclosures of image type (first match)
      - first image found in content
    Image size is ot taken in account but could in future improvements.
    '''
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
    description = post.get('description', None)
    content = post.get('content', [{}])[0].get('value') or description
    summary = post.get('summary', content)
    blogpost['summary'] = RE_STRIP_TAGS.sub('', summary).strip()

    for thumbnail in post.get('media_thumbnail', []):
        blogpost['image_url'] = thumbnail['url']
        break

    if 'image_url' not in blogpost:
        for enclosure in post.get('enclosures', []):
            if enclosure.get('type') in FEED_THUMBNAIL_MIMES:
                blogpost['image_url'] = enclosure['href']
                break

    if 'image_url' not in blogpost:
        match = RE_POST_IMG.search(content)
        if match:
            blogpost['image_url'] = match.group('src').replace('&amp;', '&')
            if match.group('srcset'):
                blogpost['srcset'] = match.group('srcset').replace('&amp;', '&')
            if match.group('sizes'):
                blogpost['sizes'] = match.group('sizes')

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


@cache.memoize(50)
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
