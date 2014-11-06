# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata import admin
from udata.frontend.views import DetailView
from udata.i18n import lazy_gettext as _

from .oauth2 import OAuth2Client


@admin.register('oauth', _('OAuth'))
class OAuthAdminView(admin.AdminView, DetailView):
    template_name = 'api/admin.html'

    def get_context(self):
        context = super(OAuthAdminView, self).get_context()
        context['clients'] = OAuth2Client.objects
        return context
