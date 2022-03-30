from datetime import datetime

import feedparser

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata_front.tests import GouvFrSettings
from udata_front.tests.frontend import GouvfrFrontTestCase


class ReuseBlueprintTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = ['admin']

    def test_render_display(self):
        '''It should render the reuse page'''
        reuse = ReuseFactory(owner=UserFactory(),
                             description='* Title 1\n* Title 2')
        url = url_for('reuses.show', reuse=reuse)
        response = self.get(url)
        self.assert200(response)
        self.assertNotIn(b'<meta name="robots" content="noindex, nofollow">',
                         response.data)
        json_ld = self.get_json_ld(response)
        self.assertEqual(json_ld['@context'], 'http://schema.org')
        self.assertEqual(json_ld['@type'], 'CreativeWork')
        self.assertEqual(json_ld['alternateName'], reuse.slug)
        self.assertEqual(json_ld['dateCreated'][:16],
                         reuse.created_at.isoformat()[:16])
        self.assertEqual(json_ld['dateModified'][:16],
                         reuse.last_modified.isoformat()[:16])
        self.assertEqual(json_ld['url'], 'http://local.test{}'.format(url))
        self.assertEqual(json_ld['name'], reuse.title)
        self.assertEqual(json_ld['description'], 'Title 1 Title 2')
        self.assertEqual(json_ld['isBasedOnUrl'], reuse.url)
        self.assertEqual(json_ld['author']['@type'], 'Person')

    def test_raise_404_if_private(self):
        '''It should raise a 404 if the reuse is private'''
        reuse = ReuseFactory(private=True)
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert404(response)

    def test_raise_410_if_deleted(self):
        '''It should raise a 410 if the reuse is deleted'''
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert410(response)

    def test_do_not_raise_410_if_deleted_but_authorized(self):
        '''It should display a dalated reuse if authorized'''
        self.login()
        reuse = ReuseFactory(deleted=datetime.now(), owner=self.user)
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the reuse page'''
        response = self.get(url_for('reuses.show', reuse='not-found'))
        self.assert404(response)

    def test_no_index_on_empty(self):
        '''It should prevent crawlers from indexing empty reuses'''
        reuse = ReuseFactory()
        url = url_for('reuses.show', reuse=reuse)
        response = self.get(url)
        self.assert200(response)
        self.assertIn(b'<meta name="robots" content="noindex, nofollow"',
                      response.data)

    def test_recent_feed(self):
        datasets = [ReuseFactory(
                    datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(prev_published_date, published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        ReuseFactory(owner=owner, datasets=[DatasetFactory()])

        response = self.get(url_for('reuses.recent_feed'))

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
        ReuseFactory(owner=owner,
                     organization=org, datasets=[DatasetFactory()])

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href,
                         self.full_url('organizations.show', org=org.id))
