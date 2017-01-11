# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.tests.frontend import FrontTestCase
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import TopicFactory


class TopicsBlueprintTest(FrontTestCase):
    def test_render_display(self):
        '''It should render a topic page'''
        with self.autoindex():
            reuses = [VisibleReuseFactory(tags=['tag-{0}'.format(i)])
                      for i in range(3)]
            datasets = [VisibleDatasetFactory(tags=['tag-{0}'.format(i)])
                        for i in range(3)]
        topic = TopicFactory(
            tags=['tag-0', 'tag-2'], datasets=datasets, reuses=reuses)

        response = self.get(url_for('topics.display', topic=topic))
        self.assert200(response)

    def test_render_display_empty(self):
        '''It should render a topic page even if empty'''
        self.init_search()
        topic = TopicFactory(tags=['tag'])

        response = self.get(url_for('topics.display', topic=topic))
        self.assert200(response)

    def test_render_datasets(self):
        '''It should render a topic datasets page'''
        with self.autoindex():
            [VisibleDatasetFactory(tags=['tag-{0}'.format(i)])
             for i in range(3)]
        topic = TopicFactory(tags=['tag-0', 'tag-2'])

        response = self.get(url_for('topics.datasets', topic=topic))
        self.assert200(response)

        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), 2)
        for dataset in rendered_datasets:
            self.assertIn(dataset.tags[0], ['tag-0', 'tag-2'])

    def test_render_datasets_empty(self):
        '''It should render a topic datasets page even if empty'''
        self.init_search()
        topic = TopicFactory(tags=['tag'])

        response = self.get(url_for('topics.datasets', topic=topic))
        self.assert200(response)

        self.assertEqual(len(self.get_context_variable('datasets')), 0)

    def test_render_reuses(self):
        '''It should render a topic reuses page'''
        with self.autoindex():
            [VisibleReuseFactory(tags=['tag-{0}'.format(i)]) for i in range(3)]
        topic = TopicFactory(tags=['tag-0', 'tag-2'])

        response = self.get(url_for('topics.reuses', topic=topic))
        self.assert200(response)

        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), 2)
        for reuse in rendered_reuses:
            self.assertIn(reuse.tags[0], ['tag-0', 'tag-2'])

    def test_render_reuses_empty(self):
        '''It should render a topic reuses page even if empty'''
        self.init_search()
        topic = TopicFactory(tags=['tag'])

        response = self.get(url_for('topics.reuses', topic=topic))
        self.assert200(response)

        self.assertEqual(len(self.get_context_variable('reuses')), 0)
