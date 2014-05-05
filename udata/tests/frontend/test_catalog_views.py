# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import StringIO
import unicodecsv

from flask import url_for

from udata.models import Dataset
from udata.core import metrics

from . import FrontTestCase
from ..factories import ResourceFactory, DatasetFactory, OrganizationFactory


class CatalogTest(FrontTestCase):
    def create_app(self):
        app = super(CatalogTest, self).create_app()
        metrics.init_app(app)
        return app

    def test_site_catalog(self):
        datasets = [DatasetFactory(resources=[ResourceFactory()]) for _ in range(3)]
        hidden_dataset = DatasetFactory()

        response = self.get(url_for('datasets.csv_catalog'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = unicodecsv.reader(csvfile, encoding='utf-8', delimiter=b',', quotechar=b'"')
        header = reader.next()
        rows = [r for r in reader]

        self.assertEqual(header[0], 'id')
        self.assertEqual(header[1], 'slug')
        self.assertEqual(header[2], 'title')

        print metrics.Metric.get_for(Dataset)
        for key, spec in metrics.Metric.get_for(Dataset).items():
            self.assertIn('metric.{0}'.format(key), header)
        # self.assertEqual(header['1'], 'slug')

        self.assertEqual(len(rows), len(datasets))
        self.assertNotIn(str(hidden_dataset.id), (row[0] for row in rows))

    def test_org_catalog(self):
        org = OrganizationFactory()
        datasets = [DatasetFactory(organization=org, resources=[ResourceFactory()]) for _ in range(3)]
        not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
        hidden_dataset = DatasetFactory()

        response = self.get(url_for('organizations.csv_catalog', org=org))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = unicodecsv.reader(csvfile, encoding='utf-8', delimiter=b',', quotechar=b'"')
        header = reader.next()
        rows = [r for r in reader]

        self.assertEqual(header[0], 'id')
        self.assertEqual(header[1], 'slug')
        self.assertEqual(header[2], 'title')
        # self.assertEqual(header['1'], 'slug')

        self.assertEqual(len(rows), len(datasets))
        self.assertNotIn(str(hidden_dataset.id), (row[0] for row in rows))
        self.assertNotIn(str(not_org_dataset.id), (row[0] for row in rows))
