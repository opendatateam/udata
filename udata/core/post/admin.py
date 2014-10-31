# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import admin
from udata.frontend.views import ListView
from udata.i18n import lazy_gettext as _
from udata.models import Post


@admin.register('posts', _('Posts'))
class PostAdminView(admin.AdminView, ListView):
    model = Post
    context_name = 'posts'
    template_name = 'post/admin.html'
