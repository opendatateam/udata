# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import


def init_app(app):
    from .views import bp
    app.register_blueprint(bp)
