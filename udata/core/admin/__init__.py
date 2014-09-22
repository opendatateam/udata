# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import redirect, url_for

from udata.core.user.permissions import sysadmin
from udata.frontend import nav, theme
from udata.frontend.views import DetailView, EditView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Issue, Site

from udata.core.site.views import SiteView
from udata.core.site.forms import SiteConfigForm

blueprint = I18nBlueprint('admin', __name__, url_prefix='/admin')

navbar = nav.Bar('admin', [])


@blueprint.route('/', endpoint='root')
def redirect_to_first_admin_tab():
    endpoint = navbar.items[0].endpoint
    return redirect(url_for(endpoint))


class AdminView(object):
    require = sysadmin

    def get_context(self):
        context = super(AdminView, self).get_context()
        current_item = None
        for item in navbar:
            if item.is_active:
                current_item = item
        context['current_item'] = current_item
        return context


def register(endpoint, label=None):
    '''A class decorator for registering admin views'''
    def wrapper(cls):
        blueprint.add_url_rule('/{0}/'.format(endpoint), view_func=cls.as_view(str(endpoint)))
        navbar.items.append(nav.Item(label or endpoint.title(), 'admin.{0}'.format(endpoint)))
        return cls
    return wrapper


@register('site', _('Site'))
class SiteAdminView(AdminView, SiteView, EditView):
    template_name = 'site/config.html'
    model = Site
    form = SiteConfigForm

    def on_form_valid(self, form):
        form.populate_obj(self.site)
        self.site.save()
        return self.get()


@register('theme', _('Theme'))
class ThemeAdminView(AdminView, SiteView, EditView):
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


@register('issues', _('Issues'))
class IssuesAdminView(AdminView, DetailView):
    template_name = 'site/issues.html'

    def get_context(self):
        context = super(IssuesAdminView, self).get_context()
        context['issues'] = Issue.objects
        return context

# site_admin.add_url_rule('/config/', view_func=SiteConfigView.as_view(str('config')))
# site_admin.add_url_rule('/theme/', view_func=SiteThemeView.as_view(str('theme')))
# site_admin.add_url_rule('/issues/', view_func=SiteIssuesView.as_view(str('issues')))
