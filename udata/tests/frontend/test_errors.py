# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import abort, url_for, Blueprint

from . import FrontTestCase


errors = Blueprint('errors', __name__)


@errors.route('/403/')
def route_403():
    abort(403)


@errors.route('/404/')
def route_404():
    abort(404)


@errors.route('/500/')
def route_500():
    abort(500)


class CustomErrorPagesTest(FrontTestCase):
    modules = ['admin', 'core.dataset', 'core.reuse', 'core.site',
               'core.organization', 'search']

    def create_app(self):
        app = super(CustomErrorPagesTest, self).create_app()
        app.register_blueprint(errors)
        return app

    def test_403(self):
        '''It should render a custom 403 page'''
        response = self.get(url_for('errors.route_403'))
        self.assert403(response)
        self.assertTemplateUsed('errors/403.html')

    def test_404(self):
        '''It should render a custom 404 page'''
        response = self.get(url_for('errors.route_404'))
        self.assert404(response)
        self.assertTemplateUsed('errors/404.html')

    def test_500(self):
        '''It should render a custom 500 page'''
        response = self.get(url_for('errors.route_500'))
        self.assert500(response)
        self.assertTemplateUsed('errors/500.html')
