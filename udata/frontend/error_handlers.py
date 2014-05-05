# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend import front, render


@front.app_errorhandler(404)
def page_not_found(error):
    return render('404.html'), 404
