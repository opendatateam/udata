# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import redirect, url_for

from udata.frontend.views import ListView
from udata.i18n import lazy_gettext as _
from udata.models import Post

from udata.core import admin


@admin.register('posts', _('Posts'))
class PostAdminView(admin.AdminView, ListView):
    model = Post
    context_name = 'posts'
    template_name = 'post/admin.html'

    # def get_context(self):
    #     context = super(PostAdminView, self).get_context()
    #     context['posts'] = Post.objects
    #     return context
