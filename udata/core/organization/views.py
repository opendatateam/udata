# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools

from flask import g, abort, redirect, url_for
from flask_security import current_user

from udata import search
from udata.frontend import csv
from udata.frontend.views import DetailView, SearchView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import (
    Organization, Reuse, Dataset, Follow, Issue, Discussion
)
from udata.sitemap import sitemap

from udata.core.dataset.csv import (
    DatasetCsvAdapter, IssuesOrDiscussionCsvAdapter, ResourcesCsvAdapter
)

from .permissions import (
    EditOrganizationPermission, OrganizationPrivatePermission
)


blueprint = I18nBlueprint('organizations', __name__,
                          url_prefix='/organizations')


@blueprint.before_app_request
def set_g_user_orgs():
    if current_user.is_authenticated:
        g.user_organizations = current_user.organizations


@blueprint.route('/', endpoint='list')
class OrganizationListView(SearchView):
    model = Organization
    context_name = 'organizations'
    template_name = 'organization/list.html'


class OrgView(object):
    model = Organization
    object_name = 'org'

    @property
    def organization(self):
        return self.get_object()

    def get_context(self):
        context = super(OrgView, self).get_context()
        context['can_edit'] = EditOrganizationPermission(self.organization)
        context['can_view'] = OrganizationPrivatePermission(self.organization)
        return context


class ProtectedOrgView(OrgView):
    def can(self, *args, **kwargs):
        permission = EditOrganizationPermission(self.organization)
        return permission.can()


@blueprint.route('/<org:org>/', endpoint='show')
class OrganizationDetailView(OrgView, DetailView):
    template_name = 'organization/display.html'
    page_size = 10

    def get_context(self):
        context = super(OrganizationDetailView, self).get_context()

        can_edit = EditOrganizationPermission(self.organization)
        can_view = OrganizationPrivatePermission(self.organization)

        if self.organization.deleted and not can_view.can():
            abort(410)

        datasets = Dataset.objects(organization=self.organization).order_by('-temporal_coverage.end', '-metrics.reuses', '-metrics.followers').visible()
        reuses = Reuse.objects(organization=self.organization).order_by('-metrics.reuses', '-metrics.followers').visible()
        followers = (Follow.objects.followers(self.organization)
                                   .order_by('follower.fullname'))
        context.update({
            'reuses': reuses.paginate(1, self.page_size),
            'datasets': datasets.paginate(1, self.page_size),
            'followers': followers,
            'can_edit': can_edit,
            'can_view': can_view,
            'private_reuses': (
                list(Reuse.objects(organization=self.object).hidden())
                if can_view else []),
            'private_datasets': (
                list(Dataset.objects(organization=self.object).hidden())
                if can_view else []),
        })
        return context


@blueprint.route('/<org:org>/dashboard/', endpoint='dashboard')
def organization_dashboard(org):
    return redirect('%s#dashboard' % url_for('organizations.show', org=org), code=301)


@blueprint.route('/<org:org>/datasets.csv', cors=True)
def datasets_csv(org):
    datasets = search.iter(Dataset, organization=str(org.id))
    adapter = DatasetCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-datasets'.format(org.slug))


@blueprint.route('/<org:org>/issues.csv', cors=True)
def issues_csv(org):
    datasets = Dataset.objects.filter(organization=str(org.id))
    issues = [Issue.objects.filter(subject=dataset)
              for dataset in datasets]
    # Turns a list of lists into a flat list.
    adapter = IssuesOrDiscussionCsvAdapter(itertools.chain(*issues))
    return csv.stream(adapter, '{0}-issues'.format(org.slug))


@blueprint.route('/<org:org>/discussions.csv', cors=True)
def discussions_csv(org):
    datasets = Dataset.objects.filter(organization=str(org.id))
    discussions = [Discussion.objects.filter(subject=dataset)
                   for dataset in datasets]
    # Turns a list of lists into a flat list.
    adapter = IssuesOrDiscussionCsvAdapter(itertools.chain(*discussions))
    return csv.stream(adapter, '{0}-discussions'.format(org.slug))


@blueprint.route('/<org:org>/datasets-resources.csv', cors=True)
def datasets_resources_csv(org):
    datasets = search.iter(Dataset, organization=str(org.id))
    adapter = ResourcesCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-datasets-resources'.format(org.slug))


@sitemap.register_generator
def sitemap_urls():
    for org in Organization.objects.visible().only('id', 'slug'):
        yield 'organizations.show_redirect', {'org': org}, None, 'weekly', 0.7
