# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .models import current_site

def init_app(app):
    @app.context_processor
    def inject_site():
        return dict(current_site=current_site)
