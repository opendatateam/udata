import logging
import requests

from flask import request, redirect, url_for, current_app, abort
from mongoengine.errors import DoesNotExist
from werkzeug.contrib.atom import AtomFeed

from udata import search
from udata.app import cache
from udata.core.activity.models import Activity
from udata.core.dataset.csv import ResourcesCsvAdapter
from udata.core.dataset.models import Dataset
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.reuse.csv import ReuseCsvAdapter
from udata.core.reuse.models import Reuse
from udata.frontend import csv
from udata_gouvfr.views.base import DetailView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.sitemap import sitemap
from udata.utils import multi_to_dict
from udata_gouvfr import theme

from udata.core.site.models import current_site

blueprint = I18nBlueprint('site', __name__)

log = logging.getLogger(__name__)


@blueprint.app_context_processor
def inject_site():
    return dict(current_site=current_site)


@blueprint.route('/activity.atom')
def activity_feed():
    activity_keys = request.args.getlist('key')

    feed = AtomFeed(
        current_app.config.get('SITE_TITLE'), feed_url=request.url,
        url=request.url_root)
    activities = (Activity.objects.order_by('-created_at')
                                  .limit(current_site.feed_size))

    for activity in activities.select_related():
        # filter by activity.key
        # /!\ this won't completely honour `feed_size` (only as a max value)
        if activity_keys and activity.key not in activity_keys:
            continue
        try:
            owner = activity.actor or activity.organization
        except DoesNotExist:
            owner = 'deleted'
            owner_url = None
        else:
            owner_url = owner.url_for(_external=True)
        try:
            related = activity.related_to
        except DoesNotExist:
            related = 'deleted'
            related_url = None
        else:
            related_url = related.url_for(_external=True)
        feed.add(
            id='%s#activity=%s' % (
                url_for('site.dashboard', _external=True), activity.id),
            title='%s by %s on %s' % (
                activity.key, owner, related),
            url=related_url,
            author={
                'name': owner,
                'uri': owner_url,
            },
            updated=activity.created_at
        )
    return feed.get_response()


@blueprint.route('/')
def home():
    context = {
        'recent_datasets': Dataset.objects.visible(),
        'recent_reuses': Reuse.objects(featured=True).visible(),
        'last_post': Post.objects.published().first()
    }
    processor = theme.current.get_processor('home')
    context = processor(context)
    return theme.render('home.html', **context)


@blueprint.route('/map/')
def map():
    return theme.render('site/map.html')


def get_export_url(model):
    did = current_app.config['EXPORT_CSV_DATASET_ID']
    dataset = Dataset.objects.get_or_404(id=did)
    resource = None
    for r in dataset.resources:
        if r.extras.get('csv-export:model', '') == model:
            resource = r
            break
    if not resource:
        abort(404)
    return resource.url


@blueprint.route('/datasets.csv')
def datasets_csv():
    params = multi_to_dict(request.args)
    # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
    exported_models = current_app.config.get('EXPORT_CSV_MODELS', [])
    if not params and 'dataset' in exported_models:
        return redirect(get_export_url('dataset'))
    params['facets'] = False
    datasets = search.iter(Dataset, **params)
    adapter = csv.get_adapter(Dataset)
    return csv.stream(adapter(datasets), 'datasets')


@blueprint.route('/resources.csv')
def resources_csv():
    params = multi_to_dict(request.args)
    # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
    exported_models = current_app.config.get('EXPORT_CSV_MODELS', [])
    if not params and 'resource' in exported_models:
        return redirect(get_export_url('resource'))
    params['facets'] = False
    datasets = search.iter(Dataset, **params)
    return csv.stream(ResourcesCsvAdapter(datasets), 'resources')


@blueprint.route('/organizations.csv')
def organizations_csv():
    params = multi_to_dict(request.args)
    # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
    exported_models = current_app.config.get('EXPORT_CSV_MODELS', [])
    if not params and 'organization' in exported_models:
        return redirect(get_export_url('organization'))
    params['facets'] = False
    organizations = search.iter(Organization, **params)
    return csv.stream(OrganizationCsvAdapter(organizations), 'organizations')


@blueprint.route('/reuses.csv')
def reuses_csv():
    params = multi_to_dict(request.args)
    # redirect to EXPORT_CSV dataset if feature is enabled and no filter is set
    exported_models = current_app.config.get('EXPORT_CSV_MODELS', [])
    if not params and 'reuse' in exported_models:
        return redirect(get_export_url('reuse'))
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


@cache.cached(50)
def get_terms_content():
    filename = current_app.config['SITE_TERMS_LOCATION']
    if filename.startswith('http'):
        # We let the error appear because:
        # - we dont want to cache false responses
        # - this is only visible on terms
        response = requests.get(filename, timeout=5)
        response.raise_for_status()
        return response.text
    else:
        with open(filename) as terms:
            return terms.read()


@blueprint.route('/terms/')
def terms():
    content = get_terms_content()
    return theme.render('terms.html', terms=content)


@sitemap.register_generator
def site_sitemap_urls():
    yield 'site.home_redirect', {}, None, 'daily', 1
    yield 'site.dashboard_redirect', {}, None, 'weekly', 0.6
    yield 'site.terms_redirect', {}, None, 'monthly', 0.2
