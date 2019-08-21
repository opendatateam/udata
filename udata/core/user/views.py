# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.frontend.views import BaseView
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('users', __name__, url_prefix='/users')

log = logging.getLogger(__name__)


@blueprint.route('/<user:user>/', endpoint='show')
class UserView(BaseView):
    pass
