# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import feedparser

from flask import url_for

from udata.core.dataset.factories import (
    ResourceFactory, DatasetFactory, LicenseFactory, CommunityResourceFactory,
    VisibleDatasetFactory
)
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.models import Follow

from . import FrontTestCase


class DatasetBlueprintTest(FrontTestCase):
    modules = ['core.dataset', 'admin', 'search', 'core.reuse', 'core.site',
               'core.organization', 'core.user', 'core.followers']

    def test_render_list(self):
        '''It should render the dataset list page'''
        with self.autoindex():
            datasets = [VisibleDatasetFactory() for i in range(3)]

        response = self.get(url_for('datasets.list'))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_list_with_facets(self):
        '''It should render the dataset list page with facets'''

        with self.autoindex():
            datasets = DatasetFactory.create_batch(3, visible=True,
                                                   org=True, geo=True)

        response = self.get(url_for('datasets.list'))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_list_with_query(self):
        '''It should render the dataset list page with a query string'''
        with self.autoindex():
            datasets = [DatasetFactory(
                resources=[ResourceFactory()]) for i in range(3)]
            expected_dataset = DatasetFactory(
                title='test for query', resources=[ResourceFactory()])
            datasets.append(expected_dataset)

        response = self.get(url_for('datasets.list'),
                            qs={'q': 'test for query'})

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), 1)
        self.assertEqual(rendered_datasets[0].id, expected_dataset.id)

    def test_render_list_empty(self):
        '''It should render the dataset list page event if empty'''
        self.init_search()
        response = self.get(url_for('datasets.list'))
        self.assert200(response)

    def test_render_display(self):
        '''It should render the dataset page'''
        dataset = VisibleDatasetFactory()
        url = url_for('datasets.show', dataset=dataset)
        response = self.get(url)
        self.assert200(response)
        self.assertNotIn(b'<meta name="robots" content="noindex, nofollow">',
                         response.data)

    def test_json_ld(self):
        '''It should render a json-ld markup into the dataset page'''
        resource = ResourceFactory(format='png',
                                   description='* Title 1\n* Title 2',
                                   metrics={'views': 10})
        license = LicenseFactory(url='http://www.datagouv.fr/licence')
        dataset = DatasetFactory(license=license,
                                 tags=['foo', 'bar'],
                                 resources=[resource],
                                 description='a&éèëù$£',
                                 owner=UserFactory(),
                                 extras={'foo': 'bar'})
        community_resource = CommunityResourceFactory(
            dataset=dataset,
            format='csv',
            description='* Title 1\n* Title 2',
            metrics={'views': 42})

        url = url_for('datasets.show', dataset=dataset)
        response = self.get(url)
        self.assert200(response)
        json_ld = self.get_json_ld(response)
        self.assertEquals(json_ld['@context'], 'http://schema.org')
        self.assertEquals(json_ld['@type'], 'Dataset')
        self.assertEquals(json_ld['@id'], str(dataset.id))
        self.assertEquals(json_ld['description'], 'a&amp;éèëù$£')
        self.assertEquals(json_ld['alternateName'], dataset.slug)
        self.assertEquals(json_ld['dateCreated'][:16],
                          dataset.created_at.isoformat()[:16])
        self.assertEquals(json_ld['dateModified'][:16],
                          dataset.last_modified.isoformat()[:16])
        self.assertEquals(json_ld['url'], 'http://local.test{}'.format(url))
        self.assertEquals(json_ld['name'], dataset.title)
        self.assertEquals(json_ld['keywords'], 'bar,foo')
        self.assertEquals(len(json_ld['distribution']), 1)

        json_ld_resource = json_ld['distribution'][0]
        self.assertEquals(json_ld_resource['@type'], 'DataDownload')
        self.assertEquals(json_ld_resource['@id'], str(resource.id))
        self.assertEquals(json_ld_resource['url'], resource.latest)
        self.assertEquals(json_ld_resource['name'], resource.title)
        self.assertEquals(json_ld_resource['contentUrl'], resource.url)
        self.assertEquals(json_ld_resource['dateCreated'][:16],
                          resource.created_at.isoformat()[:16])
        self.assertEquals(json_ld_resource['dateModified'][:16],
                          resource.modified.isoformat()[:16])
        self.assertEquals(json_ld_resource['datePublished'][:16],
                          resource.published.isoformat()[:16])
        self.assertEquals(json_ld_resource['encodingFormat'], 'png')
        self.assertEquals(json_ld_resource['contentSize'],
                          resource.filesize)
        self.assertEquals(json_ld_resource['fileFormat'], resource.mime)
        self.assertEquals(json_ld_resource['description'],
                          'Title 1 Title 2')
        self.assertEquals(json_ld_resource['interactionStatistic'],
                          {
                              '@type': 'InteractionCounter',
                              'interactionType': {
                                  '@type': 'DownloadAction',
                              },
                              'userInteractionCount': 10,
                          })

        self.assertEquals(len(json_ld['contributedDistribution']), 1)
        json_ld_resource = json_ld['contributedDistribution'][0]
        self.assertEquals(json_ld_resource['@type'], 'DataDownload')
        self.assertEquals(json_ld_resource['@id'], str(community_resource.id))
        self.assertEquals(json_ld_resource['url'], community_resource.latest)
        self.assertEquals(json_ld_resource['name'], community_resource.title)
        self.assertEquals(json_ld_resource['contentUrl'],
                          community_resource.url)
        self.assertEquals(json_ld_resource['dateCreated'][:16],
                          community_resource.created_at.isoformat()[:16])
        self.assertEquals(json_ld_resource['dateModified'][:16],
                          community_resource.modified.isoformat()[:16])
        self.assertEquals(json_ld_resource['datePublished'][:16],
                          community_resource.published.isoformat()[:16])
        self.assertEquals(json_ld_resource['encodingFormat'],
                          community_resource.format)
        self.assertEquals(json_ld_resource['contentSize'],
                          community_resource.filesize)
        self.assertEquals(json_ld_resource['fileFormat'],
                          community_resource.mime)
        self.assertEquals(json_ld_resource['description'], 'Title 1 Title 2')
        self.assertEquals(json_ld_resource['interactionStatistic'], {
            '@type': 'InteractionCounter',
            'interactionType': {
                '@type': 'DownloadAction',
            },
            'userInteractionCount': 42,
        })

        self.assertEquals(json_ld['extras'],
                          [{
                              '@type': 'http://schema.org/PropertyValue',
                              'name': 'foo',
                              'value': 'bar',
                          }])
        self.assertEquals(json_ld['license'], 'http://www.datagouv.fr/licence')
        self.assertEquals(json_ld['author']['@type'], 'Person')

    def test_json_ld_sanitize(self):
        '''Json-ld should be sanitized'''
        dataset = DatasetFactory(description='an <script>evil()</script>')
        url = url_for('datasets.show', dataset=dataset)
        response = self.get(url)
        json_ld = self.get_json_ld(response)
        self.assertEquals(json_ld['description'],
                          'an &lt;script&gt;evil()&lt;/script&gt;')

    def test_raise_404_if_private(self):
        '''It should raise a 404 if the dataset is private'''
        dataset = DatasetFactory(private=True)
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert404(response)

    def test_raise_410_if_deleted(self):
        '''It should raise a 410 if the dataset is deleted'''
        dataset = DatasetFactory(deleted=datetime.now())
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert410(response)

    def test_200_if_deleted_but_authorized(self):
        '''It should not raise a 410 if the can view it'''
        self.login()
        dataset = DatasetFactory(deleted=datetime.now(), owner=self.user)
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_no_index_on_empty(self):
        '''It should prevent crawlers from indexing empty datasets'''
        dataset = DatasetFactory()
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)
        self.assertIn(b'<meta name="robots" content="noindex, nofollow"',
                      response.data)

    def test_not_found(self):
        '''It should render the dataset page'''
        response = self.get(url_for('datasets.show', dataset='not-found'))
        self.assert404(response)

    def test_redirect_to_rdf(self):
        '''It should redirect RDF mimetypes'''
        dataset = VisibleDatasetFactory()
        url = url_for('datasets.show', dataset=dataset)
        headers = {'accept': 'text/turtle'}
        expected_url = url_for('datasets.rdf_format',
                               dataset=dataset.id,
                               format='ttl')

        response = self.get(url, headers=headers)

        self.assertRedirects(response, expected_url)

    def test_resource_latest_url(self):
        '''It should redirect to the real resource URL'''
        resource = ResourceFactory()
        DatasetFactory(resources=[resource])
        response = self.get(url_for('datasets.resource',
                                    id=resource.id))
        self.assertStatus(response, 302)
        self.assertEqual(response.location, resource.url)

    def test_community_resource_latest_url(self):
        '''It should redirect to the real community resource URL'''
        resource = CommunityResourceFactory()
        response = self.get(url_for('datasets.resource',
                                    id=resource.id))
        self.assertStatus(response, 302)
        self.assertEqual(response.location, resource.url)

    def test_resource_latest_url_404(self):
        '''It should return 404 if resource does not exists'''
        resource = ResourceFactory()
        response = self.get(url_for('datasets.resource',
                                    id=resource.id))
        self.assert404(response)

    def test_resource_latest_url_stripped(self):
        '''It should return strip extras spaces from the resource URL'''
        url = 'http://www.somewhere.com/path/with/spaces/   '
        resource = ResourceFactory(url=url)
        DatasetFactory(resources=[resource])
        response = self.get(url_for('datasets.resource',
                                    id=resource.id))
        self.assertStatus(response, 302)
        self.assertEqual(response.location, url.strip())

    def test_recent_feed(self):
        datasets = [DatasetFactory(
            resources=[ResourceFactory()]) for i in range(3)]

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(prev_published_date, published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        DatasetFactory(owner=owner, resources=[ResourceFactory()])

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, owner.fullname)
        self.assertEqual(author.href,
                         self.full_url('users.show', user=owner.id))

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        DatasetFactory(
            owner=owner, organization=org, resources=[ResourceFactory()])

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href,
                         self.full_url('organizations.show', org=org.id))

    def test_dataset_followers(self):
        '''It should render the dataset followers list page'''
        dataset = DatasetFactory()
        followers = [
            Follow.objects.create(follower=UserFactory(), following=dataset)
            for _ in range(3)
        ]

        response = self.get(url_for('datasets.followers', dataset=dataset))

        self.assert200(response)
        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))
