# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata import admin
from udata.frontend.views import DetailView
from udata.i18n import lazy_gettext as _
from udata.models import Issue


@admin.register('issues', _('Issues'))
class SiteIssuesView(admin.AdminView, DetailView):
    template_name = 'issues/admin.html'

    def get_context(self):
        context = super(SiteIssuesView, self).get_context()
        context['issues'] = Issue.objects
        return context
