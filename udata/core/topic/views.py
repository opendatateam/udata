# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, request

from udata import search
from udata.frontend import render
from udata.i18n import I18nBlueprint
from udata.models import Topic, Reuse, Dataset
from udata.utils import multi_to_dict
from udata.frontend.views import DetailView, CreateView, EditView

from .forms import TopicForm
from .permissions import TopicEditPermission

blueprint = I18nBlueprint('topics', __name__, url_prefix='/topics')


class TopicSearchQuery(search.SearchQuery):
    '''
    A SearchQuery that should also match on topic tags
    '''
    @property
    def topic(self):
        return self.kwargs['topic']

    # def initial_bool_query(self):
    #     query = super(TopicSearchQuery, self).build_text_query()
    #     self._update_bool_query(query, {'should': [{'term': {'tags': tag}} for tag in self.topic.tags]})
    #     return query

    # def get_body(self):
    #     body = super(TopicSearchQuery, self).get_body()
    #     from flask import json
    #     print json.dumps(body)
    #     return body

    def build_text_query(self):
        query = super(TopicSearchQuery, self).build_text_query()
        self._update_bool_query(query, {'should': [{'term': {'tags': tag}} for tag in self.topic.tags]})
        return query

    # def build_facet_queries(self):
    #     query = super(TopicSearchQuery, self).build_facet_queries()
    #     self._update_bool_query(query, {'should': [{'term': {'tags': tag}} for tag in self.topic.tags]})
    #     return query

    # def _bool_query(self):
    #     query = super(TopicSearchQuery, self)._bool_query()
    #     print query
    #     topic = self.kwargs['topic']
    #     query['should'].extend([{'term': {'tags': tag}} for tag in topic.tags])


@blueprint.route('/<topic:topic>/')
def display(topic):
    specs = {
        'recent_datasets': TopicSearchQuery(Dataset, sort='-created', page_size=9, topic=topic),
        'featured_reuses': TopicSearchQuery(Reuse, featured=True, page_size=6, topic=topic),
    }
    keys, queries = zip(*specs.items())

    results = search.multiquery(*queries)

    return render('topic/display.html',
        topic=topic,
        **dict(zip(keys, results))
    )


@blueprint.route('/<topic:topic>/datasets')
def datasets(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.update(topic=topic)

    return render('topic/datasets.html',
        topic=topic,
        datasets=TopicSearchQuery(Dataset, facets=True, **kwargs).execute()
    )


@blueprint.route('/<topic:topic>/reuses')
def reuses(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.update(topic=topic)

    return render('topic/reuses.html',
        topic=topic,
        reuses=TopicSearchQuery(Reuse, facets=True, **kwargs).execute()
    )


class TopicView(object):
    model = Topic
    object_name = 'topic'

    @property
    def topic(self):
        return self.get_object()


class ProtectedTopicView(TopicView):
    require = TopicEditPermission()


class TopicCreateView(ProtectedTopicView, CreateView):
    model = Topic
    form = TopicForm
    template_name = 'topic/create.html'


class TopicEditView(ProtectedTopicView, EditView):
    form = TopicForm
    template_name = 'topic/edit.html'


@blueprint.before_app_request
def store_featured_topics():
    g.featured_topics = sorted(Topic.objects(featured=True), key=lambda t: t.slug)


blueprint.add_url_rule('/new/', view_func=TopicCreateView.as_view(str('new')))
blueprint.add_url_rule('/<topic:topic>/edit/', view_func=TopicEditView.as_view(str('edit')))
