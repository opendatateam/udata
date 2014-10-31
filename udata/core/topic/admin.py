# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import admin
from udata.frontend.views import ListView
from udata.i18n import lazy_gettext as _
from udata.models import Topic


@admin.register('topics', _('Topics'))
class PostAdminView(admin.AdminView, ListView):
    model = Topic
    context_name = 'topics'
    template_name = 'topic/admin.html'
