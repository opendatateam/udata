# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import StringIO

from flask import url_for

from udata.frontend import csv

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import VisibleDatasetFactory, VisibleReuseFactory

from udata.core.tags.models import Tag
from udata.core.tags.tasks import count_tags

log = logging.getLogger(__name__)


class TagsTests(FrontTestCase):
    def test_csv(self):
        Tag.objects.create(name='datasets-only', counts={'datasets': 15})
        Tag.objects.create(name='reuses-only', counts={'reuses': 10})
        Tag.objects.create(name='both', counts={'reuses': 10, 'datasets': 15})

        response = self.get(url_for('tags.csv'))
        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = reader = csv.get_reader(csvfile)
        header = reader.next()
        rows = list(reader)

        self.assertEqual(header, ['name', 'datasets', 'reuses', 'total'])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ['both', '15', '10', '25'])
        self.assertEqual(rows[1], ['datasets-only', '15', '0', '15'])
        self.assertEqual(rows[2], ['reuses-only', '0', '10', '10'])

    def test_count(self):
        for i in range(1, 4):
            VisibleDatasetFactory(tags=['tag-{0}'.format(j) for j in range(i)])
            VisibleReuseFactory(tags=['tag-{0}'.format(j) for j in range(i)])

        count_tags.run()

        expected = {
            'tag-0': 3,
            'tag-1': 2,
            'tag-2': 1,
        }

        self.assertEqual(len(Tag.objects), len(expected))

        for name, count in expected.items():
            tag = Tag.objects.get(name=name)
            self.assertEqual(tag.total, 2 * count)
            self.assertEqual(tag.counts['datasets'], count)
            self.assertEqual(tag.counts['reuses'], count)
