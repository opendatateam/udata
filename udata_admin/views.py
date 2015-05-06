# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import theme
from udata.auth import login_required
from udata.i18n import I18nBlueprint


admin = I18nBlueprint('admin', __name__, template_folder='templates', static_folder='static')


@admin.route('/', defaults={'path': ''})
@admin.route('/<path:path>')
@login_required
def index(path):
    return theme.render('admin.html')
