import logging
import re

import feedparser
import requests

from dateutil.parser import parse
from flask import g, current_app, url_for

from udata_gouvfr import theme
from udata.app import cache
from udata.models import Dataset
from udata_gouvfr.frontend import nav
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
    nav.Item(_('News'), 'posts.list'),
    nav.Item(_('Contact us'), None, url='https://support.data.gouv.fr/'),
])

theme.menu(gouvfr_menu)

opendata_links = [
    nav.Item(_('News'), 'posts.list'),
    nav.Item(_('Reference Data'), 'gouvfr.show_page', args={'slug': 'spd/reference'}),
    nav.Item(_('Featured topics'), 'gouvfr.show_page', args={'slug': 'donnees-cles-par-sujet'}),
    nav.Item(_('Portal for European data'), None, url='https://data.europa.eu'),
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
        opendata_links.append(nav.Item(_('Data catalog'), None, url=export_url))

nav.Bar('gouvfr_opendata', opendata_links)


support_links = [
    nav.Item(_("Platform's documentation"), None, url='https://doc.data.gouv.fr'),
    nav.Item(_("Portal's API"), None, url=current_app.config.get('API_DOC_EXTERNAL_LINK', '#')),
    nav.Item(_('Open data guides'), None, url='https://guides.etalab.gouv.fr'),
    nav.Item(_('Contact us'), None, url='https://support.data.gouv.fr'),
]

nav.Bar('gouvfr_support', support_links)

footer_links = [
    nav.Item(_('Licences'), 'gouvfr.show_page', args={'slug': 'legal/licences'}),
    nav.Item(_('Terms of use'), 'site.terms'),
    nav.Item(_('Tracking and privacy'), 'gouvfr.suivi'),
    nav.Item(_('Accessibility'), 'gouvfr.show_page', args={'slug': 'legal/accessibility'}),
]

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


@theme.context('home')
def home_context(context):
    context['blogpost'] = get_blog_post(g.lang_code)
    return context
