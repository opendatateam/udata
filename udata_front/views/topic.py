# from flask import g, request

# from udata import search
# from udata.i18n import I18nBlueprint
# from udata.models import Topic
# from udata.sitemap import sitemap
# from udata.utils import multi_to_dict
# from udata_front import theme

# from udata.core.dataset.search import DatasetSearch
# from udata.core.reuse.search import ReuseSearch
# from udata.core.topic.search import topic_search_for


# blueprint = I18nBlueprint('topics', __name__, url_prefix='/topics')


# @blueprint.route('/<topic:topic>/')
# def display(topic):
#     specs = {
#         'recent_reuses': topic_search_for(topic, ReuseSearch, sort='-created', page_size=3),
#         'recent_datasets': topic_search_for(topic, DatasetSearch, sort='-created', page_size=9),
#         'featured_reuses': topic_search_for(topic, ReuseSearch, featured=True, page_size=6),
#     }
#     keys, queries = zip(*specs.items())
#     results = search.multisearch(*queries)

#     return theme.render(
#         'topic/display.html',
#         topic=topic,
#         datasets=[d for d in topic.datasets if hasattr(d, 'pk')],
#         **dict(zip(keys, results))
#     )


# @blueprint.route('/<topic:topic>/datasets')
# def datasets(topic):
#     kwargs = multi_to_dict(request.args)
#     kwargs.pop('topic', None)
#     topic_search = topic_search_for(topic,
#                                     DatasetSearch,
#                                     facets=True,
#                                     **kwargs)

#     return theme.render(
#         'topic/datasets.html',
#         topic=topic,
#         datasets=search.query(topic_search)
#     )


# @blueprint.route('/<topic:topic>/reuses')
# def reuses(topic):
#     kwargs = multi_to_dict(request.args)
#     kwargs.pop('topic', None)
#     topic_search = topic_search_for(topic,
#                                     ReuseSearch,
#                                     facets=True,
#                                     **kwargs)

#     return theme.render(
#         'topic/reuses.html',
#         topic=topic,
#         reuses=search.query(topic_search)
#     )


# @blueprint.before_app_request
# def store_featured_topics():
#     g.featured_topics = sorted(Topic.objects(featured=True),
#                                key=lambda t: t.slug)


# @sitemap.register_generator
# def sitemap_urls():
#     for topic in Topic.objects.only('id', 'slug'):
#         yield 'topics.display_redirect', {'topic': topic}, None, "weekly", 0.8
