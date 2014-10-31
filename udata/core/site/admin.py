# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import admin
from udata.frontend import theme
from udata.frontend.views import EditView
from udata.i18n import lazy_gettext as _
from udata.models import Site

from .views import SiteView
from .forms import SiteConfigForm


class SiteAdminView(SiteView, admin.AdminView):
    model = Site


@admin.register('site', _('Site'))
class SiteConfigView(SiteAdminView, EditView):
    template_name = 'site/config.html'
    form = SiteConfigForm

    def on_form_valid(self, form):
        form.populate_obj(self.site)
        self.site.save()
        return self.get()


@admin.register('theme', _('Theme'))
class SiteThemeView(SiteAdminView, EditView):
    template_name = 'site/theme.html'

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
