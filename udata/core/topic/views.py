# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, request

from udata import theme
from udata.i18n import I18nBlueprint
from udata.models import Topic, Reuse, Dataset
from udata.sitemap import sitemap
from udata.utils import multi_to_dict

from .permissions import TopicEditPermission

blueprint = I18nBlueprint('topics', __name__, url_prefix='/topics')


@blueprint.route('/<topic:topic>/')
def display(topic):
    recent_datasets = Dataset.objects(tags__in=topic.tags).order_by('-created')
    featured_reuses = Reuse.objects(tags__in=topic.tags, featured=True)

    return theme.render(
        'topic/display.html',
        topic=topic,
        datasets=[d for d in topic.datasets if hasattr(d, 'pk')],
        recent_datasets=recent_datasets.visible(),
        featured_reuses=featured_reuses.visible()
    )


@blueprint.route('/<topic:topic>/datasets')
def datasets(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.update(topic=topic)
    query = TopicSearchQuery(Dataset, facets=True, **kwargs)

    return theme.render(
        'topic/datasets.html',
        topic=topic,
        datasets=query.execute()
    )


@blueprint.route('/<topic:topic>/reuses')
def reuses(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.update(topic=topic)
    query = TopicSearchQuery(Reuse, facets=True, **kwargs)

    return theme.render(
        'topic/reuses.html',
        topic=topic,
        reuses=query.execute()
    )


class TopicView(object):
    model = Topic
    object_name = 'topic'

    @property
    def topic(self):
        return self.get_object()


class ProtectedTopicView(TopicView):
    require = TopicEditPermission()


@blueprint.before_app_request
def store_featured_topics():
    g.featured_topics = sorted(Topic.objects(featured=True),
                               key=lambda t: t.slug)


@sitemap.register_generator
def sitemap_urls():
    for topic in Topic.objects.only('id', 'slug'):
        yield 'topics.display_redirect', {'topic': topic}, None, "weekly", 0.8
