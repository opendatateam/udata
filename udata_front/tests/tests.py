import json

from html import escape

import pytest
import pytz
import requests

from flask import url_for
from feedgen.feed import FeedGenerator
from werkzeug.contrib.atom import AtomFeed

from udata.core.dataset.factories import (
    DatasetFactory, LicenseFactory, VisibleDatasetFactory
)
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.models import Badge
from udata.tests.features.territories import (
    create_geozones_fixtures
)
from udata.utils import faker
from udata.tests.helpers import assert200, assert404, assert_redirects, assert_equal_dates
from udata.frontend.markdown import md

from udata_front import APIGOUVFR_EXTRAS_KEY
from udata_front.models import SPD, TERRITORY_DATASETS
from udata_front.tests import GouvFrSettings


class GouvFrThemeTest:
    '''Ensure themed views render'''
    settings = GouvFrSettings
    modules = []

    def test_render_home(self, client):
        '''It should render the home page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)

        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_home_no_data(self, client):
        '''It should render the home page without data'''
        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_metrics(self, client):
        '''It should render the dashboard page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)
        response = client.get(url_for('site.dashboard'))
        assert200(response)

    def test_render_metrics_no_data(self, client):
        '''It should render the dashboard page without data'''
        response = client.get(url_for('site.dashboard'))
        assert200(response)

    def test_render_dataset_page(self, client):
        '''It should render the dataset page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('datasets.show', dataset=dataset))
        assert200(response)

    def test_render_dataset_w_api(self, client):
        '''It should render the dataset page'''
        dataset = DatasetFactory()
        dataset.extras[APIGOUVFR_EXTRAS_KEY] = [{
            'title': 'une API',
            'tagline': 'tagline',
            'path': '/path',
            'slug': 'slug',
            'owner': 'owner',
            'openness': 'open',
            'logo': '/logo.png',
        }]
        dataset.save()

        response = client.get(url_for('datasets.show', dataset=dataset))
        assert200(response)
        assert 'une API' in response.data.decode('utf8')

    def test_render_organization_page(self, client):
        '''It should render the organization page'''
        org = OrganizationFactory()
        datasets = [DatasetFactory(organization=org) for _ in range(3)]
        for dataset in datasets:
            ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('organizations.show', org=org))
        assert200(response)

    def test_render_reuse_page(self, client):
        '''It should render the reuse page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        reuse = ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('reuses.show', reuse=reuse))
        assert200(response)


WP_FEED_URL = 'http://somewhere.test/feed'


@pytest.mark.options(WP_ATOM_URL=WP_FEED_URL)
class GouvFrHomeBlogTest:
    '''Ensure home page render with blog'''
    settings = GouvFrSettings
    modules = []

    @pytest.fixture
    def home(self, mocker, client):
        from udata_front import theme

        def home_client(blogpost):
            mocker.patch.object(theme, 'get_blog_post', return_value=blogpost)
            return client.get(url_for('site.home'))

        return home_client

    def test_render_home_with_blog_without_thumbnail(self, home):
        '''It should render the home page with the latest blog article'''
        post = {
            'title': faker.name(),
            'link': faker.uri(),
            'summary': faker.sentence(),
            'date': faker.date_time(),
        }
        response = home(post)
        assert200(response)
        page = response.data.decode('utf8')
        assert post['title'] in page
        assert post['link'] in page
        assert post['summary'] in page
        assert 'blog-thumbnail' not in page

    def test_render_home_with_blog_with_thumbnail(self, home):
        '''It should render the home page with the latest blog article and its thumbnail'''
        post = {
            'title': faker.name(),
            'link': faker.uri(),
            'summary': faker.sentence(),
            'date': faker.date_time(),
            'image_url': faker.image_url(),
        }
        response = home(post)
        assert200(response)
        page = response.data.decode('utf8')
        assert post['title'] in page
        assert post['link'] in page
        assert post['summary'] in page
        assert post['image_url'] in page
        assert 'blog-thumbnail' in page

    def test_render_home_without_blogpost(self, home):
        '''It should render the home page when blog post is missing'''
        response = home(None)
        assert200(response)
        assert 'blog-container' not in response.data.decode('utf8')


@pytest.mark.options(WP_ATOM_URL=WP_FEED_URL)
class GetBlogPostMixin:
    '''Ensure home page render with blog'''
    settings = GouvFrSettings
    mime = None

    @pytest.fixture
    def blogpost(self, app, rmock):
        from udata_front.theme import get_blog_post

        def fixture(feed):
            if isinstance(feed, Exception):
                rmock.get(WP_FEED_URL, exc=feed)
            else:
                rmock.get(WP_FEED_URL, text=feed, headers={'Content-Type': self.mime})
            return get_blog_post('en')

        return fixture

    def test_basic_blogpost(self, blogpost):
        title = faker.sentence()
        post_url = faker.uri()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        content = faker.sentence()
        html_content = '<div>{0}</div>'.format(content)
        feed = self.feed('Some blog', title, html_content, post_url,
                         published=publish_date)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == content
        assert_equal_dates(post['date'], publish_date)
        assert 'image_url' not in post
        assert 'srcset' not in post
        assert 'sizes' not in post

    def test_blogpost_with_summary(self, blogpost):
        title = faker.sentence()
        post_url = faker.uri()
        summary = faker.sentence()
        content = faker.sentence()
        html_content = '<div>{0}</div>'.format(content)
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        feed = self.feed('Some blog', title, html_content, post_url,
                         published=publish_date,
                         summary=summary)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == summary
        assert_equal_dates(post['date'], publish_date)
        assert 'image_url' not in post
        assert 'srcset' not in post
        assert 'sizes' not in post

    def test_blogpost_with_first_image_as_thumbnail(self, blogpost):
        title = faker.sentence()
        post_url = faker.uri()
        image_url = faker.image_url()
        summary = faker.sentence()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        content = '<p><img class="whatever" src="{0}" /> {1}</p>'.format(image_url, summary)
        feed = self.feed('Some blog', title, content, post_url,
                         published=publish_date)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == summary
        assert_equal_dates(post['date'], publish_date)
        assert post['image_url'] == image_url
        assert 'srcset' not in post
        assert 'sizes' not in post

    def test_blogpost_with_first_image_as_thumbnail_and_summary(self, blogpost):
        title = faker.sentence()
        post_url = faker.uri()
        image_url = faker.image_url()
        summary = faker.sentence()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        content = '<p><img class="whatever" src="{0}" /> Whatever whatever</p>'.format(image_url)
        feed = self.feed('Some blog', title, content, post_url,
                         published=publish_date,
                         summary=summary)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == summary
        assert_equal_dates(post['date'], publish_date)
        assert post['image_url'] == image_url
        assert 'srcset' not in post
        assert 'sizes' not in post

    @pytest.mark.parametrize('tpl', [
        # Try different aatributes order
        '<p><img class="whatever" src="{0}" srcset="{1}" sizes="{2}"/> Whatever whatever</p>',
        '<p><img class="whatever" sizes="{2}" src="{0}" srcset="{1}"/> Whatever whatever</p>',
        '<p><img class="whatever" srcset="{1}" sizes="{2}" src="{0}"/> Whatever whatever</p>'
    ])
    def test_blogpost_with_first_image_as_thumbnail_as_src_set(self, blogpost, tpl):
        title = faker.sentence()
        post_url = faker.uri()
        image_url = faker.image_url()
        summary = faker.sentence()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        srcset = ', '.join(
            ' '.join((faker.image_url(width=w), '{0}w'.format(w)))
            for w in ('1200', '1024', '300')
        )
        sizes = "(max-width: 1200px) 100vw, 1200px"
        content = tpl.format(image_url, srcset, sizes)

        feed = self.feed('Some blog', title, content, post_url,
                         published=publish_date,
                         summary=summary)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == summary
        assert_equal_dates(post['date'], publish_date)
        assert post['image_url'] == image_url
        assert post['srcset'] == srcset
        assert post['sizes'] == sizes

    @pytest.mark.parametrize('mime', ['image/jpeg', 'image/png', 'image/webp'])
    def test_blogpost_with_thumbnail_as_enclosure(self, blogpost, mime):
        title = faker.sentence()
        post_url = faker.uri()
        image_url = faker.image_url()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        content = faker.sentence()
        html_content = '<div>{0}</div>'.format(content)
        feed = self.feed('Some blog', title, html_content, post_url,
                         published=publish_date,
                         enclosure={'type': mime, 'url': image_url})

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == content
        assert_equal_dates(post['date'], publish_date)
        assert post['image_url'] == image_url
        assert 'srcset' not in post
        assert 'sizes' not in post

    def test_blogpost_with_thumbnail_as_media_thumbnail(self, blogpost):
        title = faker.sentence()
        post_url = faker.uri()
        image_url = faker.image_url()
        tz = pytz.timezone(faker.timezone())
        publish_date = faker.date_time(tzinfo=tz)
        content = faker.sentence()
        html_content = '<div>{0}</div>'.format(content)
        feed = self.feed('Some blog', title, html_content, post_url,
                         published=publish_date,
                         media_thumbnail=image_url)

        post = blogpost(feed)

        assert post['title'] == title
        assert post['link'] == post_url
        assert post['summary'] == content
        assert_equal_dates(post['date'], publish_date)
        assert post['image_url'] == image_url
        assert 'srcset' not in post
        assert 'sizes' not in post

    def test_render_home_if_blog_timeout(self, blogpost):
        '''It should not fail when blog time out'''
        exc = requests.Timeout('Blog timed out')
        assert blogpost(exc) is None

    def test_render_home_if_blog_error(self, blogpost):
        '''It should not fail when blog is not available'''
        exc = requests.ConnectionError('Error')
        assert blogpost(exc) is None


class GetBlogPostAtomTest(GetBlogPostMixin):
    mime = 'application/atom+xml'

    def feed(self, feed_title, title, content, url, published=None, summary=None,
             enclosure=None, media_thumbnail=None):
        feed = AtomFeed(feed_title, feed_url=WP_FEED_URL)
        tz = pytz.timezone(faker.timezone())
        published = published or faker.date_time(tzinfo=tz)
        kwargs = {
            'content_type': 'html',
            'author': faker.name(),
            'url': url,
            'updated': faker.date_time_between(start_date=published, tzinfo=tz),
            'published': published
        }
        if summary:
            kwargs['summary'] = summary
        if enclosure:
            kwargs['links'] = [{
                'type': enclosure['type'],
                'href': enclosure['url'],
                'rel': 'enclosure',
                'length': faker.pyint(),
            }]
        feed.add(title, content, **kwargs)
        out = feed.to_string()
        if media_thumbnail:
            el = '<media:thumbnail url="{0}" />'.format(media_thumbnail)
            out = out.replace('<feed', '<feed xmlns:media="http://search.yahoo.com/mrss/"')
            out = out.replace('</entry>', '{0}</entry>'.format(el))
        return out


class GetBlogPostRssTest(GetBlogPostMixin):
    mime = 'application/rss+xml'

    def feed(self, feed_title, title, content, url, published=None, summary=None,
             enclosure=None, media_thumbnail=None):
        feed = FeedGenerator()
        feed.title(feed_title)
        feed.description(faker.sentence())
        feed.link({'href': WP_FEED_URL})

        entry = feed.add_entry()
        entry.title(title)
        entry.link({'href': url})
        entry.author(name=faker.name())
        entry.content(content, type="cdata")
        if summary:
            entry.description(summary)
        if enclosure:
            entry.enclosure(url=enclosure['url'],
                            type=enclosure['type'],
                            length=str(faker.pyint()))
        if media_thumbnail:
            feed.load_extension('media')
            entry.media.thumbnail({'url': media_thumbnail})
        tz = pytz.timezone(faker.timezone())
        published = published or faker.date_time(tzinfo=tz)
        entry.published(published)
        entry.updated(faker.date_time_between(start_date=published, tzinfo=tz))

        return feed.rss_str().decode('utf8')


@pytest.mark.options(DEFAULT_LANGUAGE='en')
class LegacyUrlsTest:
    settings = GouvFrSettings
    modules = []

    def test_redirect_datasets(self, client):
        dataset = DatasetFactory()
        response = client.get('/en/dataset/%s/' % dataset.slug)
        assert_redirects(response, url_for('datasets.show', dataset=dataset))

    def test_redirect_datasets_not_found(self, client):
        response = client.get('/en/DataSet/wtf')
        assert404(response)

    def test_redirect_organizations(self, client):
        org = OrganizationFactory()
        response = client.get('/en/organization/%s/' % org.slug)
        assert_redirects(response, url_for('organizations.show', org=org))

    def test_redirect_organization_list(self, client):
        response = client.get('/en/organization/')
        assert_redirects(response, url_for('organizations.list'))

    def test_redirect_topics(self, client):
        response = client.get('/en/group/societe/')
        assert_redirects(response, url_for('topics.display', topic='societe'))


class SpecificUrlsTest:
    settings = GouvFrSettings
    modules = []

    def test_terms(self, client):
        response = client.get(url_for('site.terms'))
        assert200(response)

    def test_licences(self, client):
        response = client.get(url_for('gouvfr.licences'))
        assert200(response)


class SpdTest:
    settings = GouvFrSettings
    modules = []

    def test_render_without_data(self, client):
        response = client.get(url_for('gouvfr.spd'))
        assert200(response)

    def test_render_with_data(self, client):
        for i in range(3):
            badge = Badge(kind=SPD)
            VisibleDatasetFactory(badges=[badge])
        response = client.get(url_for('gouvfr.spd'))
        assert200(response)


class TerritoriesSettings(GouvFrSettings):
    ACTIVATE_TERRITORIES = True
    HANDLED_LEVELS = ('fr:commune', 'fr:departement', 'fr:region')


@pytest.mark.usefixtures('clean_db')
class TerritoriesTest:
    settings = TerritoriesSettings
    modules = []

    def test_with_gouvfr_town_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=arles)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert arles.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 8
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data
        assert bdr.name in data

    def test_with_gouvfr_county_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=bdr)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert bdr.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 6
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data

    def test_with_gouvfr_region_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=paca)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert paca.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 6
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data


@pytest.mark.usefixtures('clean_db')
class OEmbedsTerritoryAPITest:
    settings = TerritoriesSettings
    modules = []

    def test_oembed_town_territory_api_get(self, api):
        '''It should fetch a town territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        odbl_license = LicenseFactory(id='odc-odbl', title='ODbL')
        LicenseFactory(id='notspecified', title='Not Specified')
        town_datasets = TERRITORY_DATASETS['commune']
        for territory_dataset_class in town_datasets.values():
            organization = OrganizationFactory(
                id=territory_dataset_class.organization_id)
            territory = territory_dataset_class(arles)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if territory_dataset_class == town_datasets['ban_odbl_com']:
                license = odbl_license
            else:
                license = licence_ouverte
            assert 'License: {title}'.format(title=license.title) in html
            assert '© {license_id}'.format(license_id=license.id) in html
            assert (
                '<a data-tooltip="Source" href="http://local.test/datasets'
                in html)

    def test_oembed_county_territory_api_get(self, api):
        '''It should fetch a county territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        LicenseFactory(id='notspecified', title='Not Specified')
        for dataset_class in TERRITORY_DATASETS['departement'].values():
            organization = OrganizationFactory(
                id=dataset_class.organization_id)
            territory = dataset_class(bdr)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if dataset_class not in (
                    TERRITORY_DATASETS['departement']['zonages_dep'], ):
                assert 'License: {0}'.format(licence_ouverte.title) in html
                assert '© {0}'.format(licence_ouverte.id) in html
                assert (
                    '<a data-tooltip="Source" href="http://local.test/datasets'
                    in html)

    def test_oembed_region_territory_api_get(self, api):
        '''It should fetch a region territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        LicenseFactory(id='notspecified', title='Not Specified')
        for territory_dataset_class in TERRITORY_DATASETS['region'].values():
            organization = OrganizationFactory(
                id=territory_dataset_class.organization_id)
            territory = territory_dataset_class(paca)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if territory_dataset_class not in (
                    TERRITORY_DATASETS['region']['zonages_reg'], ):
                assert 'License: {0}'.format(licence_ouverte.title) in html
                assert '© {0}'.format(licence_ouverte.id) in html
                assert (
                    '<a data-tooltip="Source" href="http://local.test/datasets'
                    in html)


@pytest.mark.usefixtures('clean_db')
class SpatialTerritoriesApiTest:
    settings = TerritoriesSettings
    modules = []

    def test_datasets_with_dynamic_region(self, client):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 9

    def test_datasets_with_dynamic_region_and_size(self, client):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id),
                              qs={'dynamic': 1, 'size': 2})
        assert200(response)
        assert len(response.json) == 8

    def test_datasets_without_dynamic_region(self, client):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id))
        assert200(response)
        assert len(response.json) == 3

    def test_datasets_with_dynamic_county(self, client):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[bdr.id]))

        response = client.get(url_for('api.zone_datasets', id=bdr.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 9

    def test_datasets_with_dynamic_town(self, client):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[arles.id]))

        response = client.get(url_for('api.zone_datasets', id=arles.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 11

    def test_zone_children(self, client):
        paca, bdr, arles = create_geozones_fixtures()

        response = client.get(url_for('api.zone_children', id=paca.id))
        assert200(response)
        assert response.json['features'][0]['id'] == bdr.id

        response = client.get(url_for('api.zone_children', id=bdr.id))
        assert200(response)
        assert response.json['features'][0]['id'] == arles.id

        response = client.get(url_for('api.zone_children', id=arles.id))
        assert200(response)
        assert response.json['features'] == []


@pytest.mark.usefixtures('clean_db')
class SitemapTerritoriesTest:
    settings = TerritoriesSettings
    modules = []

    def test_towns_within_sitemap(self, sitemap):
        '''It should return the towns from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=arles)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')

    def test_counties_within_sitemap(self, sitemap):
        '''It should return the counties from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=bdr)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')

    def test_regions_within_sitemap(self, sitemap):
        '''It should return the regions from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=paca)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')
