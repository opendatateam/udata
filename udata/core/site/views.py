# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request, current_app, send_from_directory, Blueprint
from werkzeug.contrib.atom import AtomFeed

from udata import search, theme
from udata.frontend import csv
from udata.frontend.views import DetailView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Dataset, Activity, Reuse, Organization, Post
from udata.utils import multi_to_dict
from udata.core.dataset.csv import ResourcesCsvAdapter
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.reuse.csv import ReuseCsvAdapter
from udata.sitemap import sitemap

from .models import current_site

noI18n = Blueprint('noI18n', __name__)
blueprint = I18nBlueprint('site', __name__)


@blueprint.app_context_processor
def inject_site():
    return dict(current_site=current_site)


@blueprint.route('/activity.atom')
def activity_feed():
    feed = AtomFeed(
        'Site activity', feed_url=request.url, url=request.url_root)
    activities = (Activity.objects.order_by('-created_at')
                                  .limit(current_site.feed_size))
    for activity in activities:
        feed.add('Activity', 'Description')
    return feed.get_response()


@blueprint.route('/')
def home():
    context = {
        'recent_datasets': Dataset.objects.visible(),
        'recent_reuses': Reuse.objects(featured=True).visible(),
        'last_post': Post.objects(private=False).first(),
    }
    processor = theme.current.get_processor('home')
    context = processor(context)
    return theme.render('home.html', **context)


@noI18n.route('/robots.txt')
def static_from_root():
    return send_from_directory(current_app.static_folder, request.path[1:])


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
class SiteDashboard(SiteView, DetailView):
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
                    'title': _('Users'),
                    'metric': 'users',
                    'type': 'bar',
                    'endpoint': 'users.list'
                }
            ]
        })

        return context


@blueprint.route('/terms/')
def terms():
    return theme.render('terms.html')


@sitemap.register_generator
def site_sitemap_urls():
    yield 'site.home_redirect', {}, None, 'daily', 1
    yield 'site.dashboard_redirect', {}, None, 'weekly', 0.6
    yield 'site.terms_redirect', {}, None, 'monthly', 0.2
