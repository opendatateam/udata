# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, request, current_app
from werkzeug.contrib.atom import AtomFeed
from werkzeug.local import LocalProxy

from udata import search
from udata.core.metrics import Metric
from udata.frontend import render, csv, theme
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Metrics, Dataset, Activity, Site, Reuse
from udata.utils import multi_to_dict


blueprint = I18nBlueprint('site', __name__)


def get_current_site():
    if getattr(g, 'site', None) is None:
        site_id = current_app.config['SITE_ID']
        g.site, _ = Site.objects.get_or_create(id=site_id, defaults={
            'title': current_app.config.get('SITE_TITLE'),
            'keywords': current_app.config.get('SITE_KEYWORDS', []),
        })
    return g.site


current_site = LocalProxy(get_current_site)


@blueprint.app_context_processor
def inject_site():
    return dict(current_site=current_site)


@blueprint.route('/activity.atom')
def activity_feed():
    feed = AtomFeed('Site activity', feed_url=request.url, url=request.url_root)
    activities = Activity.objects.order_by('-created_at').limit(current_site.feed_size)
    for activity in activities:
        feed.add('Activity', 'Description')
    # datasets = Dataset.objects.visible().order_by('-date').limit(15)
    # for dataset in datasets:
    #     author = None
    #     if dataset.organization:
    #         author = {
    #             'name': dataset.organization.name,
    #             'uri': url_for('organizations.show', org=dataset.organization, _external=True),
    #         }
    #     elif dataset.owner:
    #         author = {
    #             'name': dataset.owner.fullname,
    #             'uri': url_for('users.show', user=dataset.owner, _external=True),
    #         }
    #     feed.add(dataset.title, dataset.description,
    #              content_type='html',
    #              author=author,
    #              url=url_for('datasets.show', dataset=dataset, _external=True),
    #              updated=dataset.last_modified,
    #              published=dataset.created_at)
    return feed.get_response()


@blueprint.route('/')
def home():
    if hasattr(theme.current, 'home_context'):
        context = theme.current.home_context(theme.current)
    else:
        recent_datasets, recent_reuses = search.multiquery(
            search.SearchQuery(Dataset, sort='-created', page_size=12),
            search.SearchQuery(Reuse, sort='-created', page_size=12),
        )
        context = {
            'recent_datasets': recent_datasets,
            'recent_reuses': recent_reuses,
        }
    return render('home.html', **context)


@blueprint.route('/metrics/')
def metrics():
    metrics = Metrics.objects.last_for(current_site)
    specs = Metric.get_for('site')
    values = metrics.values if metrics else {}
    return render('metrics.html',
        metrics=dict(
            (key, {'value': values.get(key, spec.default), 'label': spec.display_name})
            for key, spec in specs.items()
        )
    )


@blueprint.route('/map/')
def map():
    return render('site/map.html')


@blueprint.route('/datasets.csv')
def datasets_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    datasets = search.iter(Dataset, **params)
    adapter = csv.get_adapter(Dataset)
    return csv.stream(adapter(datasets), 'datasets')


class SiteView(object):
    @property
    def site(self):
        return current_site

    object = site
