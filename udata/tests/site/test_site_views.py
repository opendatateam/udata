# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import StringIO

from flask import url_for

from udata.frontend import csv

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import DatasetFactory, ReuseFactory, OrganizationFactory, ResourceFactory


class SiteMetricsViewTest(FrontTestCase):
    def test_render_metrics(self):
        '''It should render the search page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organzation=org)
            ReuseFactory(organzation=org)
        response = self.get(url_for('site.metrics'))
        self.assert200(response)

    def test_render_metrics_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('site.metrics'))
        self.assert200(response)

    def test_datasets_csv(self):
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()]) for _ in range(5)]
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
        '''Should handle filtering but ignore paging'''
        with self.autoindex():
            filtered_datasets = [DatasetFactory(resources=[ResourceFactory()], tags=['selected']) for _ in range(6)]
            datasets = [DatasetFactory(resources=[ResourceFactory()]) for _ in range(3)]
            hidden_dataset = DatasetFactory()

        response = self.get(url_for('site.datasets_csv', page_size=3, tag='selected'))

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
