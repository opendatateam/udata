# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import Boolean, Completion, Date,  Object, String

from udata.core.site.views import current_site
from udata.models import (
    Reuse, Organization, Dataset, User, REUSE_TYPES
)
from udata.search import (
    BoolBooster, GaussDecay, ModelSearchAdapter, Sort,
    i18n_analyzer, metrics_mapping_for, register,
    RangeFacet, ExtrasFacet, TermsFacet, ModelTermsFacet
)
from udata.search.analysis import simple

from . import metrics  # noqa: Metrics are require for reuse search


__all__ = ('ReuseSearch', )


def max_datasets():
    return max(current_site.metrics.get('max_reuse_datasets'), 5)


def max_followers():
    return max(current_site.metrics.get('max_reuse_followers'), 10)


class ReuseTypeFacet(TermsFacet):
    def labelize(self, label, value):
        return REUSE_TYPES[value]


def reuse_badge_labelizer(label, kind):
    return Reuse.__badges__.get(kind, '')


@register
class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    fuzzy = True

    class Meta:
        doc_type = 'Reuse'

    title = String(analyzer=i18n_analyzer, fields={
        'raw': String(index='not_analyzed')
    })
    description = String(analyzer=i18n_analyzer)
    url = String()
    organization = String()
    owner = String()
    type = String()
    tags = String(index='not_analyzed', fields={
        'i18n': String(index='not_analyzed')
    })
    badges = String(index='not_analyzed')
    tag_suggest = Completion(analyzer=simple,
                             search_analyzer=simple,
                             payloads=False)
    datasets = Object(
        properties={
            'id': String(),
            'title': String(),
        }
    )
    created = Date(format='date_hour_minute_second')
    last_modified = Date(format='date_hour_minute_second')
    metrics = metrics_mapping_for(Reuse)
    featured = Boolean()
    reuse_suggest = Completion(analyzer=simple,
                               search_analyzer=simple,
                               payloads=True)
    extras = Object()

    fields = (
        'title^4',
        'description^2',
        'datasets.title',
    )
    facets = {
        'tag': TermsFacet(field='tags'),
        'organization': ModelTermsFacet(field='organization',
                                        model=Organization),
        'owner': ModelTermsFacet(field='owner', model=User),
        'dataset': ModelTermsFacet(field='dataset.id', model=Dataset),
        # 'type': ReuseTypeFacet(field='type'),
        # 'datasets': RangeFacet(field='metrics.datasets'),
        # 'followers': RangeFacet(field='metrics.followers'),
        'extra': ExtrasFacet(field='extras'),
        'badge': TermsFacet(field='badges', labelizer=reuse_badge_labelizer),
    }
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'datasets': Sort('metrics.datasets'),
        'followers': Sort('metrics.followers'),
        'views': Sort('metrics.views'),
    }
    boosters = [
        BoolBooster('featured', 1.1),
        GaussDecay('metrics.datasets', max_datasets, decay=0.8),
        GaussDecay('metrics.followers', max_followers, decay=0.8),
    ]

    @classmethod
    def is_indexable(cls, reuse):
        return (reuse.deleted is None and
                len(reuse.datasets) > 0 and
                not reuse.private)

    @classmethod
    def serialize(cls, reuse):
        """By default use the ``to_dict`` method

        and exclude ``_id``, ``_cls`` and ``owner`` fields.
        """
        return {
            'title': reuse.title,
            'description': reuse.description,
            'url': reuse.url,
            'organization': (str(reuse.organization.id)
                             if reuse.organization else None),
            'owner': str(reuse.owner.id) if reuse.owner else None,
            'type': reuse.type,
            'tags': reuse.tags,
            'tag_suggest': reuse.tags,
            'badges': [badge.kind for badge in reuse.badges],
            'created': reuse.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': reuse.last_modified.strftime('%Y-%m-%dT%H:%M:%S'),
            'dataset': [{
                'id': str(d.id),
                'title': d.title
            } for d in reuse.datasets if isinstance(d, Dataset)],
            'metrics': reuse.metrics,
            'featured': reuse.featured,
            'extras': reuse.extras,
            'reuse_suggest': {
                'input': cls.completer_tokenize(reuse.title) + [reuse.id],
                'output': str(reuse.id),
                'payload': {
                    'title': reuse.title,
                    'slug': reuse.slug,
                    'image_url': reuse.image(40),
                },
            },
        }
