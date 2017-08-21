# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from udata.auth import current_user

def init_app(app):
    from .models import Follow
    @app.template_global()
    @app.template_filter()
    def is_following(obj):
        if not current_user.is_authenticated:
            return False
        return Follow.objects.is_following(current_user._get_current_object(), obj)
