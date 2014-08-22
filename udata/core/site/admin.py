# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import redirect, url_for

from udata import tasks
from udata.core.user.permissions import sysadmin
from udata.frontend import nav, theme
from udata.frontend.views import DetailView, EditView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Issue, Site

from .views import SiteView
from .forms import SiteConfigForm

site_admin = I18nBlueprint('site_admin', __name__, url_prefix='/admin')

navbar = nav.Bar('site_admin', [
    nav.Item(_('General'), 'site_admin.config'),
    nav.Item(_('Theme'), 'site_admin.theme'),
    nav.Item(_('Issues'), 'site_admin.issues'),
    nav.Item(_('Jobs'), 'site_admin.jobs'),
])


@site_admin.route('/', endpoint='root')
def redirect_to_first_admin_tab():
    return redirect(url_for('site_admin.config'))


class SiteAdminView(SiteView):
    require = sysadmin

    def get_context(self):
        context = super(SiteAdminView, self).get_context()
        current_item = None
        for item in navbar:
            if item.is_active:
                current_item = item
        context['current_item'] = current_item
        return context


@site_admin.route('/config/', endpoint='config')
class SiteConfigView(SiteAdminView, EditView):
    template_name = 'site/config.html'
    model = Site
    form = SiteConfigForm

    def on_form_valid(self, form):
        form.populate_obj(self.site)
        self.site.save()
        return self.get()


@site_admin.route('/theme/', endpoint='theme')
class SiteThemeView(SiteAdminView, EditView):
    template_name = 'site/theme.html'
    model = Site

    def get_form(self, data, obj=None):
        if theme.current.admin_form:
            theme_config = theme.current.config
            return theme.current.admin_form(data, data=theme_config)
        else:
            return None

    def on_form_valid(self, form):
        self.site.themes[theme.current.identifier] = form.data
        self.site.save()
        return self.get()


@site_admin.route('/issues/', endpoint='issues')
class SiteIssuesView(SiteAdminView, DetailView):
    template_name = 'site/issues.html'

    def get_context(self):
        context = super(SiteIssuesView, self).get_context()
        context['issues'] = Issue.objects
        return context


@site_admin.route('/jobs/', endpoint='jobs')
class SiteJobsView(SiteAdminView, DetailView):
    template_name = 'site/jobs.html'

    def get_context(self):
        context = super(SiteJobsView, self).get_context()
        context['schedulables'] = tasks.schedulables()
        context['jobs'] = tasks.PeriodicTask.objects
        return context
