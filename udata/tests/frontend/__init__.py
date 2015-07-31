# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests import TestCase, WebTestMixin, SearchTestMixin

from udata import frontend, api
from udata.i18n import I18nBlueprint

# Temporary fix to have the admin blueprint in context before we integrate
# it directly within the udata core.
admin = I18nBlueprint('admin', __name__)


@admin.route('/admin/', defaults={'path': ''})
@admin.route('/admin/<path:path>')
def index(path):
    pass
# End of fix, don't forget the registerd blueprint below.


class FrontTestCase(WebTestMixin, SearchTestMixin, TestCase):
    def create_app(self):
        app = super(FrontTestCase, self).create_app()
        app.register_blueprint(admin)
        api.init_app(app)
        frontend.init_app(app)
        return app
