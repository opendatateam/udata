# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, request, current_app
from werkzeug.contrib.atom import AtomFeed
from werkzeug.local import LocalProxy

from udata import search, theme
from udata.frontend import csv
from udata.frontend.views import DetailView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Dataset, Activity, Site, Reuse, Organization
from udata.utils import multi_to_dict

from udata.core.activity.views import ActivityView
from udata.core.dataset.csv import ResourcesCsvAdapter

from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.reuse.csv import ReuseCsvAdapter

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


def default_home_context_processor(context):
    recent_datasets, recent_reuses = search.multiquery(
        search.SearchQuery(Dataset, sort='-created', page_size=12),
        search.SearchQuery(Reuse, sort='-created', page_size=12),
    )
    context.update(recent_datasets=recent_datasets, recent_reuses=recent_reuses)
    return context


@blueprint.route('/')
def home():
    context = {}
    processor = theme.current.get_processor('home', default_home_context_processor)
    return theme.render('home.html', **processor(context))


@blueprint.route('/map/')
def map():
    return theme.render('site/map.html')


@blueprint.route('/datasets.csv')
def datasets_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    datasets = search.iter(Dataset, **params)
    adapter = csv.get_adapter(Dataset)
    return csv.stream(adapter(datasets), 'datasets')


@blueprint.route('/resources.csv')
def resources_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    datasets = search.iter(Dataset, **params)
    return csv.stream(ResourcesCsvAdapter(datasets), 'resources')


@blueprint.route('/organizations.csv')
def organizations_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    organizations = search.iter(Organization, **params)
    return csv.stream(OrganizationCsvAdapter(organizations), 'organizations')


@blueprint.route('/reuses.csv')
def reuses_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    reuses = search.iter(Reuse, **params)
    return csv.stream(ReuseCsvAdapter(reuses), 'reuses')


class SiteView(object):
    @property
    def site(self):
        return current_site

    object = site


@blueprint.route('/dashboard/', endpoint='dashboard')
class SiteDashboard(SiteView, ActivityView, DetailView):
    template_name = 'site/dashboard.html'

    def get_context(self):
        context = super(SiteDashboard, self).get_context()

        context['metrics'] = ({
            'title': _('Data'),
            'widgets': [
                {
                    'title': _('Datasets'),
                    'metric': 'datasets',
                    'type': 'line',
                    'endpoint': 'datasets.list',
                },
                {
                    'title': _('Reuses'),
                    'metric': 'reuses',
                    'type': 'line',
                    'endpoint': 'reuses.list',
                },
                {
                    'title': _('Resources'),
                    'metric': 'resources',
                    'type': 'line',
                }
            ]
        }, {
            'title': _('Community'),
            'widgets': [
                {
                    'title': _('Organizations'),
                    'metric': 'organizations',
                    'type': 'bar',
                    'endpoint': 'organizations.list',
                },
                {
                    'title': _('Public services'),
                    'metric': 'public_services',
                    'type': 'bar',
                    'endpoint': 'organizations.list',
                    'args': {'public_services': True}
                },
                {
                    'title': _('Users'),
                    'metric': 'users',
                    'type': 'bar',
                    'endpoint': 'users.list'
                }
            ]
        })

        return context
