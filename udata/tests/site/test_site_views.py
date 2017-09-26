# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import StringIO

from datetime import datetime

from flask import url_for

from udata.frontend import csv
from udata.models import Badge, Site, PUBLIC_SERVICE

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.site.models import current_site
from udata.core.reuse.factories import ReuseFactory
from udata.tests.frontend import FrontTestCase


class SiteViewsTest(FrontTestCase):
    modules = ['core.site', 'admin', 'core.dataset', 'core.reuse',
               'core.organization', 'search']

    def test_site_global(self):
        '''It should create and/or load the current site'''
        with self.app.test_request_context(''):
            self.app.preprocess_request()
            self.assertIsInstance(current_site._get_current_object(), Site)
            self.assertEqual(current_site.id, self.app.config['SITE_ID'])

    def test_render_home(self):
        '''It should render the home page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)

        current_site.settings.home_datasets = [
            DatasetFactory() for _ in range(3)]
        current_site.settings.home_reuses = [
            ReuseFactory() for _ in range(3)]

        response = self.get(url_for('site.home'))
        self.assert200(response)

    def test_render_home_no_data(self):
        '''It should render the home page without data'''
        response = self.get(url_for('site.home'))
        self.assert200(response)

    def test_render_dashboard(self):
        '''It should render the search page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_render_dashboard_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_datasets_csv(self):
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()])
                        for _ in range(5)]
            hidden_dataset = DatasetFactory()

        response = self.get(url_for('site.datasets_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(datasets))
        for dataset in datasets:
            self.assertIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)

    def test_datasets_csv_with_filters(self):
        '''Should handle filtering but ignore paging or facets'''
        with self.autoindex():
            filtered_datasets = [
                DatasetFactory(resources=[ResourceFactory()],
                               tags=['selected'])
                for _ in range(6)]
            datasets = [DatasetFactory(resources=[ResourceFactory()])
                        for _ in range(3)]
            hidden_dataset = DatasetFactory()

        response = self.get(
            url_for(
                'site.datasets_csv', tag='selected', page_size=3, facets=True))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        # Should ignore paging
        self.assertEqual(len(rows), len(filtered_datasets))
        # SHoulf pass filter
        for dataset in filtered_datasets:
            self.assertIn(str(dataset.id), ids)
        for dataset in datasets:
            self.assertNotIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)

    def test_resources_csv(self):
        with self.autoindex():
            datasets = [
                DatasetFactory(resources=[ResourceFactory(),
                                          ResourceFactory()])
                for _ in range(3)]
            DatasetFactory()

        response = self.get(url_for('site.resources_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'dataset.id')
        self.assertIn('dataset.title', header)
        self.assertIn('dataset.url', header)
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('filetype', header)
        self.assertIn('url', header)
        self.assertIn('created_at', header)
        self.assertIn('modified', header)
        self.assertIn('downloads', header)

        resource_id_index = header.index('id')

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        self.assertEqual(len(rows), sum(len(d.resources) for d in datasets))
        for dataset in datasets:
            for resource in dataset.resources:
                self.assertIn((str(dataset.id), str(resource.id)), ids)

    def test_resources_csv_with_filters(self):
        '''Should handle filtering but ignore paging or facets'''
        with self.autoindex():
            filtered_datasets = [DatasetFactory(resources=[ResourceFactory(),
                                                           ResourceFactory()],
                                                tags=['selected'])
                                 for _ in range(6)]
            [DatasetFactory(resources=[ResourceFactory()]) for _ in range(3)]
            DatasetFactory()

        response = self.get(
            url_for('site.resources_csv', tag='selected', page_size=3,
                    facets=True))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'dataset.id')
        self.assertIn('dataset.title', header)
        self.assertIn('dataset.url', header)
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('filetype', header)
        self.assertIn('url', header)
        self.assertIn('created_at', header)
        self.assertIn('modified', header)
        self.assertIn('downloads', header)

        resource_id_index = header.index('id')

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        self.assertEqual(len(rows),
                         sum(len(d.resources) for d in filtered_datasets))
        for dataset in filtered_datasets:
            for resource in dataset.resources:
                self.assertIn((str(dataset.id), str(resource.id)), ids)

    def test_organizations_csv(self):
        with self.autoindex():
            orgs = [OrganizationFactory() for _ in range(5)]
            hidden_org = OrganizationFactory(deleted=datetime.now())

        response = self.get(url_for('site.organizations_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('name', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(orgs))
        for org in orgs:
            self.assertIn(str(org.id), ids)
        self.assertNotIn(str(hidden_org.id), ids)

    def test_organizations_csv_with_filters(self):
        '''Should handle filtering but ignore paging or facets'''
        user = self.login()
        with self.autoindex():
            public_service_badge = Badge(
                kind=PUBLIC_SERVICE,
                created_by=user
            )
            filtered_orgs = [
                OrganizationFactory(badges=[public_service_badge])
                for _ in range(6)]
            orgs = [OrganizationFactory() for _ in range(3)]
            hidden_org = OrganizationFactory(deleted=datetime.now())

        response = self.get(
            url_for('site.organizations_csv', badge=PUBLIC_SERVICE,
                    page_size=3, facets=True))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('name', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        # Should ignore paging
        self.assertEqual(len(rows), len(filtered_orgs))
        # SHoulf pass filter
        for org in filtered_orgs:
            self.assertIn(str(org.id), ids)
        for org in orgs:
            self.assertNotIn(str(org.id), ids)
        self.assertNotIn(str(hidden_org.id), ids)

    def test_reuses_csv(self):
        with self.autoindex():
            reuses = [ReuseFactory(datasets=[DatasetFactory()])
                      for _ in range(5)]
            hidden_reuse = ReuseFactory()

        response = self.get(url_for('site.reuses_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(reuses))
        for reuse in reuses:
            self.assertIn(str(reuse.id), ids)
        self.assertNotIn(str(hidden_reuse.id), ids)

    def test_reuses_csv_with_filters(self):
        '''Should handle filtering but ignore paging or facets'''
        with self.autoindex():
            filtered_reuses = [
                ReuseFactory(datasets=[DatasetFactory()], tags=['selected'])
                for _ in range(6)]
            reuses = [ReuseFactory(datasets=[DatasetFactory()])
                      for _ in range(3)]
            hidden_reuse = ReuseFactory()

        response = self.get(
            url_for('site.reuses_csv', tag='selected', page_size=3,
                    facets=True))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        # Should ignore paging
        self.assertEqual(len(rows), len(filtered_reuses))
        # SHoulf pass filter
        for reuse in filtered_reuses:
            self.assertIn(str(reuse.id), ids)
        for reuse in reuses:
            self.assertNotIn(str(reuse.id), ids)
        self.assertNotIn(str(hidden_reuse.id), ids)

    def test_map_view(self):
        response = self.get(url_for('site.map'))
        self.assert200(response)

    def test_terms_view(self):
        response = self.client.get(url_for('site.terms'))
        self.assert200(response)
