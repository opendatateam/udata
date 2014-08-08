# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, request
from werkzeug.contrib.atom import AtomFeed

from udata import search
from udata.core.metrics import Metric
from udata.core.user.permissions import sysadmin
from udata.frontend import render, csv, nav
from udata.frontend.views import DetailView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Metrics, Dataset, Issue, Activity
from udata.utils import multi_to_dict


blueprint = I18nBlueprint('site', __name__)


@blueprint.before_app_request
def set_g_site():
    g.site = None


FEED_SIZE = 20


@blueprint.route('/activity.atom')
def activity_feed():
    feed = AtomFeed('Site activity', feed_url=request.url, url=request.url_root)
    activities = Activity.objects.order_by('-created_at').limit(FEED_SIZE)
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


@blueprint.route('/metrics/')
def metrics():
    metrics = Metrics.objects.last_for('site')
    specs = Metric.get_for('site')
    values = metrics.values if metrics else {}
    return render('metrics.html',
        metrics=dict(
            (key, {'value': values.get(key, spec.default), 'label': spec.display_name})
            for key, spec in specs.items()
        )
    )


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
        return self.get_object()

    def get_object(self):
        return g.site


navbar = nav.Bar('site_admin', [
    nav.Item(_('Issues'), 'site.issues'),
])


class SiteAdminView(SiteView):
    require = sysadmin


class SiteIssuesView(SiteAdminView, DetailView):
    template_name = 'site/issues.html'

    def get_context(self):
        context = super(SiteIssuesView, self).get_context()
        context['issues'] = Issue.objects
        return context


blueprint.add_url_rule('/site/issues/', view_func=SiteIssuesView.as_view(str('issues')))
