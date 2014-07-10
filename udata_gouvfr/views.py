# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, redirect

from udata.frontend import render
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('gouvfr', __name__, template_folder='templates')


@blueprint.route('/dataset/<dataset>/')
def redirect_datasets(dataset):
    return redirect(url_for('datasets.show', dataset=dataset))


@blueprint.route('/organization/<org>/')
def redirect_organizations(org):
    return redirect(url_for('organizations.show', org=org))


@blueprint.route('/Redevances')
def redevances():
    return render('redevances.html')
