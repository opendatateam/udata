# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import redirect, url_for

from udata.frontend.views import ListView
from udata.i18n import lazy_gettext as _
from udata.models import Topic

from udata.core import admin


@admin.register('topics', _('Topics'))
class PostAdminView(admin.AdminView, ListView):
    model = Topic
    context_name = 'topics'
    template_name = 'topic/admin.html'

    # def get_context(self):
    #     context = super(PostAdminView, self).get_context()
    #     context['posts'] = Post.objects
    #     return context
