# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request, g, jsonify, redirect, url_for
from flask.ext.security import current_user

from udata import search
from udata.forms import OrganizationForm, OrganizationMemberForm, OrganizationExtraForm
from udata.frontend import nav, csv
from udata.frontend.views import DetailView, CreateView, EditView, SearchView, BaseView, SingleObject
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Organization, Member, Reuse, Dataset, ORG_ROLES, User, Follow, FollowOrg, Issue
from udata.utils import get_by

from udata.core.dataset.csv import DatasetCsvAdapter

from .permissions import EditOrganizationPermission


blueprint = I18nBlueprint('organizations', __name__, url_prefix='/organizations')


@blueprint.before_app_request
def set_g_user_orgs():
    if current_user.is_authenticated():
        g.user_organizations = Organization.objects(members__user=current_user.id)


navbar = nav.Bar('edit_org', [
    nav.Item(_('Descrition'), 'organizations.edit'),
    # nav.Item(_('Additional informations'), 'organizations.edit_extras'),
    nav.Item(_('Members'), 'organizations.edit_members'),
    nav.Item(_('Membership request'), 'organizations.edit_membership_requests'),
    nav.Item(_('Teams'), 'organizations.edit_teams'),
    nav.Item(_('Issues'), 'organizations.issues')
])


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
        for item in navbar.items:
            item._args = {'org': self.organization}
        return super(OrgView, self).get_context()


class ProtectedOrgView(OrgView):
    def can(self, *args, **kwargs):
        permission = EditOrganizationPermission(self.organization.id)
        return permission.can()


class OrganizationDetailView(OrgView, DetailView):
    template_name = 'organization/display.html'
    nb_followers = 16

    def get_context(self):
        context = super(OrganizationDetailView, self).get_context()

        org_id = str(self.organization.id)
        datasets, supplied_datasets, reuses = search.multiquery(
            search.SearchQuery(Dataset, sort='-created', organization=org_id, page_size=9),
            search.SearchQuery(Dataset, sort='-created', supplier=org_id, page_size=9),
            search.SearchQuery(Reuse, sort='-created', organization=org_id, page_size=9),

        )
        followers = FollowOrg.objects.followers(self.organization).order_by('follower.fullname')

        context.update({
            'reuses': reuses,
            'datasets': datasets,
            'supplied_datasets': supplied_datasets,
            'private_reuses': list(Reuse.objects(organization=self.object, private=True)),
            'private_datasets': list(Dataset.objects(organization=self.object, private=True)),
            'followers': followers[:self.nb_followers],
            'can_edit': EditOrganizationPermission(self.organization.id)
        })

        return context


class OrganizationCreateView(CreateView):
    model = Organization
    form = OrganizationForm
    template_name = 'organization/create.html'


class OrganizationEditView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit.html'


class OrganizationDeleteView(ProtectedOrgView, SingleObject, BaseView):
    def post(self, org):
        org.deleted = datetime.now()
        org.save()
        return redirect(url_for('organizations.show', org=self.organization))


class OrganizationEditMembersView(ProtectedOrgView, EditView):
    form = OrganizationMemberForm
    template_name = 'organization/edit_members.html'

    def get_context(self):
        context = super(OrganizationEditMembersView, self).get_context()
        context['roles'] = ORG_ROLES
        return context

    def on_form_valid(self, form):
        user = User.objects.get_or_404(id=form.pk.data)
        member = get_by(self.organization.members, 'user', user)
        if member:
            member.role = form.value.data
        else:
            member = Member(user=user, role=form.value.data or 'editor')
            self.organization.members.append(member)
        self.organization.save()
        return '', 200

    def on_form_error(self, form):
        return '', 400

    def delete(self, **kwargs):
        self.kwargs = kwargs
        user = User.objects.get_or_404(id=request.form.get('user_id'))
        member = get_by(self.organization.members, 'user', user)
        self.organization.members.remove(member)
        self.organization.save()
        return '', 204


class OrganizationMembershipRequestsView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit_membership_requests.html'


class OrganizationExtrasEditView(ProtectedOrgView, EditView):
    form = OrganizationExtraForm
    template_name = 'organization/edit_extras.html'

    def on_form_valid(self, form):
        if form.old_key.data:
            del self.organization.extras[form.old_key.data]
        self.organization.extras[form.key.data] = form.value.data
        self.organization.save()
        return jsonify({'key': form.key.data, 'value': form.value.data})


class OrganizationExtraDeleteView(ProtectedOrgView, SingleObject, BaseView):
    def delete(self, org, extra, **kwargs):
        del org.extras[extra]
        org.save()
        return ''


class OrganizationEditTeamsView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit_teams.html'


class OrganizationEditAlertsView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit_alerts.html'


class OrganizationIssuesView(ProtectedOrgView, DetailView):
    template_name = 'organization/issues.html'

    def get_context(self):
        context = super(OrganizationIssuesView, self).get_context()
        datasets = Dataset.objects(organization=self.organization)
        reuses = Reuse.objects(organization=self.organization)
        ids = [o.id for o in list(datasets) + list(reuses)]
        context['issues'] = Issue.objects(subject__in=ids)
        return context


@blueprint.route('/<org:org>/datasets.csv')
def datasets_csv(org):
    datasets = search.iter(Dataset, organization=str(org.id))
    adapter = DatasetCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-datasets'.format(org.slug))


@blueprint.route('/<org:org>/supplied-datasets.csv')
def supplied_datasets_csv(org):
    datasets = search.iter(Dataset, supplier=str(org.id))
    adapter = DatasetCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-supplied-datasets'.format(org.slug))


blueprint.add_url_rule('/', view_func=OrganizationListView.as_view(str('list')))
blueprint.add_url_rule('/new/', view_func=OrganizationCreateView.as_view(str('new')))
blueprint.add_url_rule('/<org:org>/', view_func=OrganizationDetailView.as_view(str('show')))
blueprint.add_url_rule('/<org:org>/edit/', view_func=OrganizationEditView.as_view(str('edit')))
blueprint.add_url_rule('/<org:org>/edit/members/', view_func=OrganizationEditMembersView.as_view(str('edit_members')))
blueprint.add_url_rule('/<org:org>/edit/requests/', view_func=OrganizationMembershipRequestsView.as_view(str('edit_membership_requests')))
blueprint.add_url_rule('/<org:org>/edit/teams/', view_func=OrganizationEditTeamsView.as_view(str('edit_teams')))
blueprint.add_url_rule('/<org:org>/issues/', view_func=OrganizationIssuesView.as_view(str('issues')))
blueprint.add_url_rule('/<org:org>/edit/extras/', view_func=OrganizationExtrasEditView.as_view(str('edit_extras')))
blueprint.add_url_rule('/<org:org>/edit/extras/<string:extra>/', view_func=OrganizationExtraDeleteView.as_view(str('delete_extra')))
blueprint.add_url_rule('/<org:org>/delete/', view_func=OrganizationDeleteView.as_view(str('delete')))
