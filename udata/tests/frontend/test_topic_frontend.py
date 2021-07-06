from udata import search
from udata.tests import SearchTestMixin, TestCase
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.topic.factories import TopicFactory
from udata.core.topic.search import topic_search_for


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
