# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, url_for

from udata.i18n import I18nBlueprint

from . import WebTestMixin, TestCase


bp = I18nBlueprint('i18nbp', __name__)


@bp.route('/lang/')
def lang():
    return g.lang_code


class I18nBlueprintTest(WebTestMixin, TestCase):
    def create_app(self):
        app = super(I18nBlueprintTest, self).create_app()
        app.config['DEFAULT_LANGUAGE'] = 'en'
        app.config['LANGUAGES'] = {
            'en': 'English',
            'fr': 'Français',
        }
        app.register_blueprint(bp)
        return app

    def test_lang_inserted_url_for(self):
        self.assertEqual(url_for('i18nbp.lang'), '/en/lang/')

    def test_redirect_url_for(self):
        self.assertEqual(url_for('i18nbp.lang_redirect'), '/lang/')

    def test_redirect_on_missing_lang(self):
        response = self.get('/lang/')
        self.assertRedirects(response, '/en/lang/')

    def test_do_not_redirect_and_set_lang(self):
        self.assertEqual(self.get('/fr/lang/').data, 'fr')
        self.assertEqual(self.get('/en/lang/').data, 'en')

    def test_redirect_on_default_lang_for_unknown_lang(self):
        self.assertRedirects(self.get('/sk/lang/'), '/en/lang/')

    def test_404_on_default_lang_for_unknown_lang(self):
        self.assert404(self.get('/sk/not-found/'))
