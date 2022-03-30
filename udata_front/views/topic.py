from flask import g, request

from udata.i18n import I18nBlueprint
from udata.models import Topic
from udata.sitemap import sitemap
from udata.utils import multi_to_dict
from udata_front import theme


blueprint = I18nBlueprint('topics', __name__, url_prefix='/topics')


@blueprint.route('/<topic:topic>/')
def display(topic):

    return theme.render(
        'topic/display.html',
        topic=topic,
        datasets=[],
    )


@blueprint.route('/<topic:topic>/datasets')
def datasets(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.pop('topic', None)

    return theme.render(
        'topic/datasets.html',
        topic=topic,
        datasets=[]
    )


@blueprint.route('/<topic:topic>/reuses')
def reuses(topic):
    kwargs = multi_to_dict(request.args)
    kwargs.pop('topic', None)

    return theme.render(
        'topic/reuses.html',
        topic=topic,
        reuses=[]
    )


@blueprint.before_app_request
def store_featured_topics():
    g.featured_topics = sorted(Topic.objects(featured=True),
                               key=lambda t: t.slug)


@sitemap.register_generator
def sitemap_urls():
    for topic in Topic.objects.only('id', 'slug'):
        yield 'topics.display_redirect', {'topic': topic}, None, "weekly", 0.8
