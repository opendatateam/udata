from elasticsearch_dsl import Q

from udata import search


class TopicSearchMixin(object):
    def __init__(self, topic, params):
        self.topic = topic
        super(TopicSearchMixin, self).__init__(params)

    def search(self):
        '''Override search to match on topic tags'''
        s = super(TopicSearchMixin, self).search()
        s = s.query('bool', should=[
            Q('term', tags=tag) for tag in self.topic.tags
        ])
        return s


def topic_search_for(topic, adapter, **kwargs):
    facets = search.facets_for(adapter, kwargs)
    faceted_search_class = adapter.facet_search(*facets)

    class TopicSearch(TopicSearchMixin, faceted_search_class):
        pass

    return TopicSearch(topic, kwargs)
