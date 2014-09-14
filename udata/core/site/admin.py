# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import redirect, url_for

from udata.core.user.permissions import sysadmin
from udata.forms import model_form
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
])


# @navbar.initializer
# def insert_them_tab(nav):
#     print 'initializer'
#     if theme.current and hasattr(theme.current, 'config_class'):
#         print 'has config'
#         navbar = nav['site_admin']
#         navbar.items.insert(1, nav.Item(_('Theme configuration'), 'site_admin.theme'))


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


class SiteConfigView(SiteAdminView, EditView):
    template_name = 'site/config.html'
    model = Site
    form = SiteConfigForm

    def on_form_valid(self, form):
        form.populate_obj(self.site)
        self.site.save()
        return self.get()


class SiteThemeView(SiteAdminView, EditView):
    template_name = 'site/theme.html'
    model = Site

    def get_form(self, data, obj=None):
        config = self.site.themes.get(theme.current.identifier)
        if hasattr(theme.current, 'form'):
            return theme.current.form(data, config)
        elif hasattr(theme.current, 'config_class'):
            form = model_form(theme.current.config_class)
            return form(data, config)
        else:
            return None

    def on_form_valid(self, form):
        form.populate_obj(theme.current.config)
        self.site.save()
        return self.get()


class SiteIssuesView(SiteAdminView, DetailView):
    template_name = 'site/issues.html'

    def get_context(self):
        context = super(SiteIssuesView, self).get_context()
        context['issues'] = Issue.objects
        return context

site_admin.add_url_rule('/config/', view_func=SiteConfigView.as_view(str('config')))
site_admin.add_url_rule('/theme/', view_func=SiteThemeView.as_view(str('theme')))
site_admin.add_url_rule('/issues/', view_func=SiteIssuesView.as_view(str('issues')))
