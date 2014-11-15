# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import theme
from udata.frontend import front


@front.app_errorhandler(403)
def forbidden(error):
    return theme.render('errors/403.html', error=error), 403


@front.app_errorhandler(404)
def page_not_found(error):
    return theme.render('errors/404.html', error=error), 404


@front.app_errorhandler(500)
def internal_error(error):
    return theme.render('errors/500.html', error=error), 500
