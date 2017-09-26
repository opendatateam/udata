# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import StringIO

from flask import url_for

from udata.frontend import csv

from udata.tests import TestCase
from udata.tests.frontend import FrontTestCase
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.tags.models import Tag
from udata.core.tags.tasks import count_tags
from udata.tags import tags_list, normalize, slug, MAX_TAG_LENGTH

log = logging.getLogger(__name__)


class TagsTests(FrontTestCase):
    modules = ['core.tags']

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
            # Tags should be normalized and deduplicated.
            tags = ['Tag "{0}"'.format(j) for j in range(i)] + ['tag-0']
            VisibleDatasetFactory(tags=tags)
            VisibleReuseFactory(tags=tags)

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


class TagsUtilsTest(TestCase):

    def test_tags_list(self):
        self.assertEquals([], tags_list(''))
        self.assertEquals(['a'], tags_list('a'))
        self.assertEquals(['a', 'b', 'c'],
                          sorted(tags_list('a, b, c')))
        self.assertEquals(['a-b', 'c-d', 'e'],
                          sorted(tags_list('a b, c d, e')))

    def test_tags_list_strip(self):
        self.assertEquals(['a', 'b', 'c'],
                          sorted(tags_list('a, b ,  ,,, c')))
        self.assertEquals(['a-b', 'c-d', 'e'],
                          sorted(tags_list('  a b ,  c   d, e ')))

    def test_tags_list_deduplication(self):
        self.assertEquals(['a-b', 'c-d', 'e'],
                          sorted(tags_list('a b, c d,  a  b , e')))

    def test_slug_empty(self):
        self.assertEquals('', slug(''))

    def test_slug_several_words(self):
        self.assertEquals('la-claire-fontaine',
                          slug('la claire fontaine'))

    def test_slug_accents(self):
        self.assertEquals('ecole-publique', slug('école publique'))

    def test_slug_case(self):
        self.assertEquals('ecole-publique', slug('EcoLe publiquE'))

    def test_slug_consecutive_spaces(self):
        self.assertEquals('ecole-publique', slug('ecole  publique'))

    def test_slug_special_characters(self):
        self.assertEquals('ecole-publique', slug('ecole-publique'))
        self.assertEquals('ecole-publique', slug('ecole publique.'))
        self.assertEquals('ecole-publique', slug('ecole publique-'))
        self.assertEquals('ecole-publique', slug('ecole publique_'))

    def test_normalize(self):
        self.assertEquals('', normalize(''))
        self.assertEquals('', normalize('a'))
        self.assertEquals('', normalize('aa'))
        self.assertEquals('aaa', normalize('aaa'))
        self.assertEquals('a' * MAX_TAG_LENGTH, normalize('a' * (MAX_TAG_LENGTH + 1)))
        self.assertEquals('aaa-a', normalize('aAa a'))
