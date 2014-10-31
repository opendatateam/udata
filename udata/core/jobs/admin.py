# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import admin
from udata.frontend.views import DetailView
from udata.i18n import lazy_gettext as _
from udata.core.site.admin import SiteAdminView

from .models import PeriodicTask


@admin.register('jobs', _('Jobs'))
class SiteJobsView(SiteAdminView, DetailView):
    template_name = 'jobs/admin.html'

    def get_context(self):
        context = super(SiteJobsView, self).get_context()
        context['jobs'] = PeriodicTask.objects
        return context
