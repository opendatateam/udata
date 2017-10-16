# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import Boolean, Completion, Date,  Object, String

from udata.i18n import lazy_gettext as _
from udata.core.site.models import current_site
from udata.models import (
    Reuse, Organization, Dataset, User, REUSE_TYPES
)
from udata.search import (
    BoolBooster, GaussDecay, ModelSearchAdapter,
    i18n_analyzer, metrics_mapping_for, register,
    RangeFacet, TermsFacet, ModelTermsFacet, BoolFacet
)
from udata.search.analysis import simple

from . import metrics  # noqa: Metrics are require for reuse search


__all__ = ('ReuseSearch', )


def max_datasets():
    return max(current_site.metrics.get('max_reuse_datasets'), 5)


def max_followers():
    return max(current_site.metrics.get('max_reuse_followers'), 10)


def reuse_type_labelizer(value):
    return REUSE_TYPES[value]


def reuse_badge_labelizer(kind):
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
    url = String(index='not_analyzed')
    organization = String(index='not_analyzed')
    owner = String(index='not_analyzed')
    type = String(index='not_analyzed')
    tags = String(index='not_analyzed', fields={
        'i18n': String(index='not_analyzed')
    })
    badges = String(index='not_analyzed')
    tag_suggest = Completion(analyzer=simple,
                             search_analyzer=simple,
                             payloads=False)
    datasets = Object(
        properties={
            'id': String(index='not_analyzed'),
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
        'type': TermsFacet(field='type', labelizer=reuse_type_labelizer),
        'datasets': RangeFacet(field='metrics.datasets',
                               ranges=[('none', (None, 1)),
                                       ('few', (1, 5)),
                                       ('many', (5, None))],
                               labels={
                                    'none': _('No datasets'),
                                    'few': _('Few datasets'),
                                    'many': _('Many datasets'),
                               }),
        'followers': RangeFacet(field='metrics.followers',
                                ranges=[('none', (None, 1)),
                                        ('few', (1, 5)),
                                        ('many', (5, None))],
                                labels={
                                     'none': _('No followers'),
                                     'few': _('Few followers'),
                                     'many': _('Many followers'),
                                }),
        'badge': TermsFacet(field='badges', labelizer=reuse_badge_labelizer),
        'featured': BoolFacet(field='featured'),
    }
    sorts = {
        'title': 'title.raw',
        'created': 'created',
        'last_modified': 'last_modified',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
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
        datasets = Dataset.objects(id__in=[r.id for r in reuse.datasets])
        datasets = list(datasets.only('id', 'title').no_dereference())
        organization = None
        owner = None
        if reuse.organization:
            organization = Organization.objects(id=reuse.organization.id).first()
        elif reuse.owner:
            owner = User.objects(id=reuse.owner.id).first()
        return {
            'title': reuse.title,
            'description': reuse.description,
            'url': reuse.url,
            'organization': str(organization.id) if organization else None,
            'owner': str(owner.id) if owner else None,
            'type': reuse.type,
            'tags': reuse.tags,
            'tag_suggest': reuse.tags,
            'badges': [badge.kind for badge in reuse.badges],
            'created': reuse.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': reuse.last_modified.strftime('%Y-%m-%dT%H:%M:%S'),
            'dataset': [{
                'id': str(d.id),
                'title': d.title
            } for d in datasets],
            'metrics': reuse.metrics,
            'featured': reuse.featured,
            'extras': reuse.extras,
            'reuse_suggest': {
                'input': cls.completer_tokenize(reuse.title) + [reuse.id],
                'output': str(reuse.id),
                'payload': {
                    'title': reuse.title,
                    'slug': reuse.slug,
                    'image_url': reuse.image(40, external=True),
                },
            },
        }
