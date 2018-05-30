from flask import url_for

from udata import search
from udata.tests import SearchTestMixin, TestCase
from udata.tests.frontend import FrontTestCase
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import TopicFactory
from udata.core.topic.views import topic_search_for


class TopicSearchTest(SearchTestMixin, TestCase):
    def test_empty_search_no_match(self):
        '''Should return no result if no data match the tags'''
        with self.autoindex():
            VisibleDatasetFactory.create_batch(2, tags=['whatever'])
        topic = TopicFactory(tags=['no-match'])

        query = topic_search_for(topic, DatasetSearch)
        result = search.query(query)

        self.assertEqual(len(result), 0)

    def test_empty_search_with_match(self):
        '''Should only return data with at least one tag'''
        with self.autoindex():
            included = VisibleDatasetFactory.create_batch(2, tags=['in'])
            excluded = VisibleDatasetFactory.create_batch(2, tags=['out'])
        topic = TopicFactory(tags=['in', 'no-match'])

        query = topic_search_for(topic, DatasetSearch)
        result = search.query(query)

        found = [d.id for d in result]

        self.assertEqual(len(found), 2)

        for dataset in included:
            self.assertIn(dataset.id, found)
        for dataset in excluded:
            self.assertNotIn(dataset.id, found)

    def test_empty_search_with_filter_and_match(self):
        '''Should match both the topic criteria and the query'''
        with self.autoindex():
            # Match both the topic condition but the queried tag
            match = VisibleDatasetFactory.create_batch(2, tags=[
                'in', 'filtered'
            ])
            # Match the topic condition but not the queried tag
            no_match = VisibleDatasetFactory.create_batch(2, tags=['in'])
            # Excluded because not matching one of the topic tag
            excluded = VisibleDatasetFactory.create_batch(2, tags=[
                'out', 'filtered'
            ])
        topic = TopicFactory(tags=['in', 'no-match'])

        query = topic_search_for(topic, DatasetSearch, tag='filtered')
        result = search.query(query)

        found = [d.id for d in result]

        self.assertEqual(len(found), 2)

        for dataset in match:
            self.assertIn(dataset.id, found)
        for dataset in no_match + excluded:
            self.assertNotIn(dataset.id, found)


class TopicsBlueprintTest(FrontTestCase):
    modules = ['core.topic', 'admin', 'core.dataset', 'core.reuse',
               'core.site', 'core.organization', 'search']

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

    def test_render_datasets_with_topic_param(self):
        '''Should render a topic datasets page even with a topic parameter'''
        self.init_search()
        topic = TopicFactory(tags=['tag'])

        url = url_for('topics.datasets', topic=topic, qs={'topic': 'whatever'})
        response = self.get(url)
        self.assert200(response)

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

    def test_render_reuses_with_topic_parameter(self):
        '''Should render a topic reuses page even with a topic parameter'''
        self.init_search()
        topic = TopicFactory(tags=['tag'])

        url = url_for('topics.reuses', topic=topic, qs={'topic': 'whatever'})
        response = self.get(url)
        self.assert200(response)
