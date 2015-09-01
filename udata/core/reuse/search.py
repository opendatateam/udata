# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.site.views import current_site
from udata.models import (
    Reuse, Organization, Dataset, User, REUSE_TYPES, REUSE_BADGE_KINDS
)
from udata.search import BoolBooster, GaussDecay
from udata.search import (
    ModelSearchAdapter, Sort, i18n_analyzer, metrics_mapping
)
from udata.search import RangeFacet, BoolFacet, ExtrasFacet
from udata.search import TermFacet, ModelTermFacet

# Metrics are require for reuse search
from . import metrics


__all__ = ('ReuseSearch', )


max_datasets = lambda: max(current_site.metrics.get('max_reuse_datasets'), 5)
max_followers = lambda: max(current_site.metrics.get('max_reuse_followers'),
                            10)


class ReuseTypeFacet(TermFacet):
    def labelize(self, label, value):
        return REUSE_TYPES[value]


def reuse_badge_labelizer(label, kind):
    return REUSE_BADGE_KINDS.get(kind, '')


class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    fuzzy = True
    fields = (
        'title^4',
        'description^2',
        'datasets.title',
    )
    facets = {
        'tag': TermFacet('tags'),
        'organization': ModelTermFacet('organization', Organization),
        'owner': ModelTermFacet('owner', User),
        'dataset': ModelTermFacet('dataset.id', Dataset),
        'type': ReuseTypeFacet('type'),
        'datasets': RangeFacet('metrics.datasets'),
        'followers': RangeFacet('metrics.followers'),
        'featured': BoolFacet('featured'),
        'extra': ExtrasFacet('extras'),
        'badge': TermFacet('badges', labelizer=reuse_badge_labelizer),
    }
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'datasets': Sort('metrics.datasets'),
        'followers': Sort('metrics.followers'),
        'views': Sort('metrics.views'),
    }
    mapping = {
        'properties': {
            'title': {
                'type': 'string',
                'analyzer': i18n_analyzer,
                'fields': {
                    'raw': {'type': 'string', 'index': 'not_analyzed'}
                }
            },
            'description': {'type': 'string', 'analyzer': i18n_analyzer},
            'url': {'type': 'string'},
            'organization': {'type': 'string'},
            'owner': {'type': 'string'},
            'type': {'type': 'string'},
            'tags': {
                'type': 'string',
                'index_name': 'tag',
                'index': 'not_analyzed'
            },
            'tag_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': False,
            },
            'badges': {
                'type': 'string',
                'index_name': 'badges',
                'index': 'not_analyzed'
            },
            'created': {'type': 'date', 'format': 'date_hour_minute_second'},
            'last_modified': {
                'type': 'date',
                'format': 'date_hour_minute_second'
            },
            'dataset': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'title': {'type': 'string'}
                }
            },
            'metrics': metrics_mapping(Reuse),
            'featured': {'type': 'boolean'},
            'reuse_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
            'extras': {
                'type': 'object',
                'index_name': 'extra',
            },
        }
    }
    boosters = [
        BoolBooster('featured', 1.1),
        GaussDecay('metrics.datasets', max_datasets, decay=0.8),
        GaussDecay('metrics.followers', max_followers, decay=0.8),
    ]

    @classmethod
    def is_indexable(cls, reuse):
        return (reuse.deleted is None
                and len(reuse.datasets) > 0
                and not reuse.private)

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
