# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import current_user

from udata.i18n import I18nBlueprint

from .models import Follow

blueprint = I18nBlueprint('followers', __name__)


@blueprint.app_template_global()
@blueprint.app_template_filter()
def is_following(obj):
    if not current_user.is_authenticated:
        return False
    return Follow.objects.is_following(current_user._get_current_object(), obj)
