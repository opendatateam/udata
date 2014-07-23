# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, g

from udata.auth import current_user
from udata.frontend import nav
from udata.frontend.views import DetailView, EditView, ListView
from udata.models import User, Activity, Organization, Dataset, Reuse
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.forms import UserProfileForm, UserSettingsForm, UserAPIKeyForm, UserNotificationsForm

from .permissions import sysadmin, UserEditPermission

blueprint = I18nBlueprint('users', __name__, url_prefix='/u')


@blueprint.before_app_request
def set_g_sysadmin():
    g.sysadmin = sysadmin


@blueprint.app_context_processor
def inject_sysadmin_perms():
    return {'sysadmin': sysadmin}


navbar = nav.Bar('edit_user', [
    nav.Item(_('Profile'), 'users.edit'),
    nav.Item(_('Settings'), 'users.settings'),
    nav.Item(_('API KEY'), 'users.apikey_settings'),
    nav.Item(_('Notifications'), 'users.notifications_settings'),
])


class UserListView(ListView):
    model = User
    template_name = 'user/list.html'
    context_name = 'users'

    def get_queryset(self):
        return User.objects.order_by('first_name', 'last_name')


class UserView(object):
    model = User
    object_name = 'user'

    @property
    def user(self):
        return self.get_object()

    def get_context(self):
        context = super(UserView, self).get_context()
        context['organizations'] = Organization.objects(members__user=self.user)
        for item in navbar.items:
            item._args = {'user': self.user}
        return context


class UserEditView(UserView):
    def get_context(self):
        for item in navbar.items:
            item._args = {'user': self.user}
        return super(UserEditView, self).get_context()

    def can(self, *args, **kwargs):
        permission = UserEditPermission(self.user)
        return permission.can()


class UserProfileEditView(UserEditView, EditView):
    form = UserProfileForm
    template_name = 'user/edit.html'

    def get_success_url(self):
        return url_for('users.show', user=self.object)


class UserSettingsView(UserEditView, EditView):
    form = UserSettingsForm
    template_name = 'user/edit_settings.html'

    def get_success_url(self):
        return url_for('users.show', user=self.object)


class UserAPIKeySettingsView(UserEditView, EditView):
    form = UserAPIKeyForm
    template_name = 'user/edit_apikey.html'

    def on_form_valid(self, form):
        if form.action.data == 'generate':
            self.user.generate_api_key()
        else:
            self.user.clear_api_key()
        self.user.save()
        return self.render()


class UserNotificationsView(UserEditView, EditView):
    form = UserNotificationsForm
    template_name = 'user/edit_notifications.html'

    def get_success_url(self):
        return url_for('users.show', user=self.object)


class UserDatasetsView(UserView, DetailView):
    template_name = 'user/datasets.html'

    def get_context(self):
        context = super(UserDatasetsView, self).get_context()
        context['datasets'] = Dataset.objects(owner=self.user).visible()
        return context


class UserReusesView(UserView, DetailView):
    template_name = 'user/reuses.html'

    def get_context(self):
        context = super(UserReusesView, self).get_context()
        context['reuses'] = Reuse.objects(owner=self.user).visible()
        return context


class UserActivityView(UserView, DetailView):
    template_name = 'user/activity.html'

    def get_context(self):
        context = super(UserActivityView, self).get_context()
        context['activities'] = Activity.objects(actor=self.object).order_by('-created_at')
        return context


blueprint.add_url_rule('/', view_func=UserListView.as_view(str('list')))
blueprint.add_url_rule('/<user:user>/', view_func=UserActivityView.as_view(str('show')))
blueprint.add_url_rule('/<user:user>/edit/', view_func=UserProfileEditView.as_view(str('edit')))
blueprint.add_url_rule('/<user:user>/activity/', view_func=UserActivityView.as_view(str('activity')))
blueprint.add_url_rule('/<user:user>/datasets/', view_func=UserDatasetsView.as_view(str('datasets')))
blueprint.add_url_rule('/<user:user>/reuses/', view_func=UserReusesView.as_view(str('reuses')))

blueprint.add_url_rule('/<user:user>/edit/settings/', view_func=UserSettingsView.as_view(str('settings')))
blueprint.add_url_rule('/<user:user>/edit/apikey/', view_func=UserAPIKeySettingsView.as_view(str('apikey_settings')))
blueprint.add_url_rule('/<user:user>/edit/notifications/', view_func=UserNotificationsView.as_view(str('notifications_settings')))
