# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import


def init_app(app):
    from . import api  # noqa
    from .views import admin
    app.register_blueprint(admin, url_prefix='/admin')
