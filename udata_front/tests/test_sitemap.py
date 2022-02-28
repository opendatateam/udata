from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import VisibleReuseFactory
# from udata.core.topic.factories import TopicFactory

from udata_front.tests import GouvFrSettings


class SitemapTest:
    settings = GouvFrSettings
    modules = []

    # def test_topics_within_sitemap(self, sitemap):
    #     '''It should return a topic list from the sitemap.'''
    #     topics = TopicFactory.create_batch(3)

    #     sitemap.fetch()

    #     for topic in topics:
    #         url = sitemap.get_by_url('topics.display_redirect', topic=topic)
    #         assert url is not None
    #         # assert url is not None
    #         sitemap.assert_url(url, 0.8, 'weekly')

    def test_organizations_within_sitemap(self, sitemap):
        '''It should return an organization list from the sitemap.'''
        organizations = OrganizationFactory.create_batch(3)

        sitemap.fetch()

        for org in organizations:
            url = sitemap.get_by_url('organizations.show_redirect', org=org)
            assert url is not None
            sitemap.assert_url(url, 0.7, 'weekly')

    def test_reuses_within_sitemap(self, sitemap):
        '''It should return a reuse list from the sitemap.'''
        reuses = VisibleReuseFactory.create_batch(3)

        sitemap.fetch()

        for reuse in reuses:
            url = sitemap.get_by_url('reuses.show_redirect', reuse=reuse)
            assert url is not None
            sitemap.assert_url(url, 0.8, 'weekly')

    def test_datasets_within_sitemap(self, sitemap):
        '''It should return a dataset list from the sitemap.'''
        datasets = VisibleDatasetFactory.create_batch(3)

        sitemap.fetch()

        for dataset in datasets:
            url = sitemap.get_by_url('datasets.show_redirect', dataset=dataset)
            assert url is not None
            sitemap.assert_url(url, 0.8, 'weekly')

    def test_posts_within_sitemap(self, sitemap):
        '''It should return a post list from the sitemap.'''
        posts = PostFactory.create_batch(3)

        sitemap.fetch()

        for post in posts:
            url = sitemap.get_by_url('posts.show_redirect', post=post)
            assert url is not None
            sitemap.assert_url(url, 0.6, 'weekly')

    def test_home_within_sitemap(self, sitemap):
        '''It should return the home page from the sitemap.'''
        sitemap.fetch()

        url = sitemap.get_by_url('site.home_redirect')
        assert url is not None
        sitemap.assert_url(url, 1, 'daily')

    def test_dashboard_within_sitemap(self, sitemap):
        '''It should return the dashoard page from the sitemap.'''
        sitemap.fetch()

        url = sitemap.get_by_url('site.dashboard_redirect')
        assert url is not None
        sitemap.assert_url(url, 0.6, 'weekly')

    def test_terms_within_sitemap(self, sitemap):
        '''It should return the terms page from the sitemap.'''
        sitemap.fetch()

        url = sitemap.get_by_url('site.terms_redirect')
        assert url is not None

    def test_https_sitemap(self, sitemap):
        '''It should handle https sitemap.'''
        sitemap.fetch(secure=True)

        url = sitemap.get_by_url('site.home_redirect', _scheme='https')
        assert url is not None
        sitemap.assert_url(url, 1, 'daily')
        loc = url.xpath('s:loc', namespaces=sitemap.NAMESPACES)[0].text
        assert loc.startswith('https://')
